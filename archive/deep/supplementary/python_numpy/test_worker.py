import json
from pathlib import Path
import random
import subprocess
import tempfile
import unittest

import main

ROOT = Path(__file__).resolve().parent


class WorkerTests(unittest.TestCase):
    def test_examples(self):
        self.assertEqual(main.invoice({'events': [{'id': 'e1', 'customer': ' A ', 'amount_cents': 150, 'status': 'paid'}]}),
                         {'customers': [{'customer': 'A', 'gross_cents': 150, 'refund_cents': 0, 'net_cents': 150, 'count': 1}], 'accepted': 1, 'duplicates': 0, 'ignored': 0, 'rejected': 0, 'gross_cents': 150, 'refund_cents': 0, 'net_cents': 150})
        self.assertEqual(main.telemetry({'samples': [-2, 5, 8, 1], 'window': 2, 'threshold': 3}),
                         {'count': 3, 'min': 1, 'max': 6, 'above': 2, 'weighted_checksum': 25})
        self.assertEqual(main.access_log({'start_ms': 100, 'end_ms': 200, 'events': [{'ts_ms': 120, 'route': ' /api/orders ', 'status': 503, 'duration_us': 1234, 'bytes': 20}]}),
                         {'routes': [{'route': '/api/orders', 'count': 1, 'errors': 1, 'total_bytes': 20, 'max_us': 1234, 'p95_us': 1234}], 'total_count': 1, 'total_errors': 1, 'total_bytes': 20})

    def test_invoice_rules(self):
        def event(i, c, a, s):
            return dict(id=i, customer=c, amount_cents=a, status=s)
        events = [event('bad', ' \t\v\f\r\n', 10, 'paid'), event('bad', 'X', 100, 'paid'),
                  event('p', 'X', -1, 'pending'), event('q', 'X', 0, 'unknown'),
                  event('v', 'X', 10, 'void'), event('w', 'X', 10, 'pending'),
                  event('1', ' \tAA\v\f', 2**40, 'paid'), event('2', 'AA', 2**40, 'refund'),
                  event('3', 'B', 0, 'paid'), event('3', '', -1, 'bad'),
                  event('4', 'A', 1, 'refund')]
        r = main.invoice({'events': events})
        self.assertEqual([x['customer'] for x in r['customers']], ['A', 'AA', 'B'])
        self.assertEqual((r['accepted'], r['duplicates'], r['ignored'], r['rejected']), (4, 2, 2, 3))
        self.assertEqual(r['net_cents'], -1)
        self.assertEqual(r['customers'][1]['net_cents'], 0)
        self.assertEqual(main.invoice({'events': []})['customers'], [])

    def test_access_boundaries_and_percentiles(self):
        for n in range(1, 202):
            events = [dict(ts_ms=10, route=' \t/r\f', status=500 if i % 2 else 499,
                           duration_us=i * 2**35, bytes=2**36) for i in reversed(range(n))]
            events.extend([dict(ts_ms=t, route='excluded', status=599, duration_us=0, bytes=1) for t in (9, 20)])
            r = main.access_log(dict(start_ms=10, end_ms=20, events=events))
            row = r['routes'][0]
            self.assertEqual(len(r['routes']), 1)
            self.assertEqual(row['p95_us'], (((95*n + 99)//100)-1)*2**35)
            self.assertEqual(row['max_us'], (n-1)*2**35)
            self.assertEqual(r['total_bytes'], n*2**36)
            self.assertEqual(r['total_errors'], n//2)
        r = main.access_log(dict(start_ms=10, end_ms=10, events=events))
        self.assertEqual(r, dict(routes=[], total_count=0, total_errors=0, total_bytes=0))

    def test_invoice_fees(self):
        def event(i, c, a, s='paid'):
            return dict(id=i, customer=c, amount_cents=a, status=s)
        events = [event('1', ' A ', 5), event('2', 'A', 5),
                  event('3', 'B', 4), event('4', 'B', 15),
                  event('5', 'C', 100, 'refund'), event('6', 'D', 0),
                  event('1', 'A', 10000), event('bad', '', 100),
                  event('bad', 'A', 100), event('neg', 'A', -1),
                  event('unknown', 'A', 100, 'other'),
                  event('p', 'A', 100, 'pending'), event('v', 'A', 100, 'void')]
        legacy = main.invoice(dict(events=events))
        zero = main.invoice(dict(events=events, fee_bps=0))
        charged = main.invoice(dict(events=events, fee_bps=1000))
        expected = dict(legacy, fee_cents=4, net_cents=legacy['net_cents']-4,
                        customers=[dict(row, fee_cents=fee, net_cents=row['net_cents']-fee)
                                   for row, fee in zip(legacy['customers'], [2, 2, 0, 0])])
        self.assertEqual(charged, expected)
        self.assertEqual(zero, dict(legacy, fee_cents=0,
                                   customers=[dict(row, fee_cents=0) for row in legacy['customers']]))
        self.assertNotIn('fee_cents', legacy)
        self.assertTrue(all('fee_cents' not in row for row in legacy['customers']))
        self.assertEqual(main.invoice(dict(events=[])),
                         dict(customers=[], accepted=0, duplicates=0, ignored=0, rejected=0,
                              gross_cents=0, refund_cents=0, net_cents=0))
        self.assertEqual(main.invoice(dict(events=[], fee_bps=0))['fee_cents'], 0)
        self.assertEqual(main.invoice(dict(events=[], fee_bps=1000))['fee_cents'], 0)
        # Values and products above 32 bits, near the promised safe integer bound.
        for bps in (0, 1, 333, 1000):
            amount = ((2**53-1)-5000)//max(bps, 1)
            result = main.invoice(dict(events=[event('large', 'A', amount)], fee_bps=bps))
            fee = (amount*bps+5000)//10000
            self.assertEqual(result['fee_cents'], fee)
            self.assertEqual(result['customers'][0]['fee_cents'], fee)
            self.assertEqual(result['net_cents'], amount-fee)

    def test_invoice_fee_random_reference(self):
        rng = random.Random(217)
        for _ in range(150):
            events = [dict(id=str(rng.randrange(60)), customer=rng.choice([' A ', 'B', 'AA', '']),
                           amount_cents=rng.randrange(-2, 10**9),
                           status=rng.choice(['paid', 'refund', 'pending', 'void', 'bad']))
                      for _ in range(150)]
            first = {}
            for event in events:
                first.setdefault(event['id'], event)
            bps = rng.randrange(1001)
            legacy = main.invoice(dict(events=events))
            expected = dict(legacy, customers=[])
            total_fee = 0
            for row in legacy['customers']:
                fee = sum((e['amount_cents']*bps+5000)//10000 for e in first.values()
                          if e['customer'].strip(main.ASCII_WHITESPACE) == row['customer']
                          and e['amount_cents'] >= 0 and e['status'] == 'paid')
                total_fee += fee
                expected['customers'].append(dict(row, fee_cents=fee, net_cents=row['net_cents']-fee))
            expected.update(fee_cents=total_fee, net_cents=legacy['net_cents']-total_fee)
            self.assertEqual(main.invoice(dict(events=events, fee_bps=bps)), expected)

    def test_telemetry_random_reference(self):
        rng = random.Random(91234)
        for _ in range(1500):
            n = rng.randrange(1, 100)
            samples = [rng.randrange(-2**38, 2**38) for _ in range(n)]
            w = rng.randrange(1, n+1)
            threshold = rng.randrange(-2**38, 2**38)
            averages = []
            for i in range(n-w+1):
                s = sum(samples[i:i+w])
                q, _ = divmod(abs(s), w)
                averages.append(-q if s < 0 else q)
            expected = dict(count=len(averages), min=min(averages), max=max(averages),
                            above=sum(a > threshold for a in averages),
                            weighted_checksum=sum(i*a for i, a in enumerate(averages, 1)))
            self.assertEqual(main.telemetry(dict(samples=samples, window=w, threshold=threshold)), expected)
        for w in (-10, 0, 3):
            self.assertEqual(main.telemetry(dict(samples=[1, 2], window=w, threshold=0)), {'error': 'invalid_window'})
        for value in (-(2**53-1), 2**53-1):
            r = main.telemetry(dict(samples=[value], window=1, threshold=0))
            self.assertEqual(r['weighted_checksum'], value)

    def test_unknown_operations_and_route_order(self):
        for value in ({}, [], None, {"op": []}, {"op": {}}, {"op": 123}):
            self.assertEqual(main.process_line(json.dumps(value).encode()), {"error": "unknown_op"})
        events = [dict(ts_ms=0, route=r, status=200, duration_us=0, bytes=0)
                  for r in ('B', 'AA', ' A ', ' \t', 'AA')]
        rows = main.access_log(dict(start_ms=0, end_ms=1, events=events))['routes']
        self.assertEqual([r['route'] for r in rows], ['', 'A', 'AA', 'B'])
        self.assertEqual(rows[2]['count'], 2)
        self.assertEqual(main.telemetry(dict(samples=[], window=1, threshold=0)),
                         {'error': 'invalid_window'})

    def test_telemetry_exact_int64_boundaries(self):
        bound = 2**53 - 1
        cases = [([bound, -bound, -bound, bound], 1),
                 ([-bound, bound - 1], 2),
                 ([bound - 1, -bound], 2),
                 ([-bound, 0], 2),
                 ([bound, 0], 2),
                 ([-5, 2, -4, 7, -1], 2),
                 ([bound, -bound, 7, -8], 4)]
        for samples, window in cases:
            with self.subTest(samples=samples, window=window):
                sums = [sum(samples[i:i + window])
                        for i in range(len(samples) - window + 1)]
                averages = [s // window if s >= 0 else -((-s) // window)
                            for s in sums]
                expected = dict(count=len(averages), min=min(averages),
                                max=max(averages), above=sum(a > 0 for a in averages),
                                weighted_checksum=sum(i * a for i, a in enumerate(averages, 1)))
                self.assertEqual(main.telemetry(dict(samples=samples, window=window,
                                                     threshold=0)), expected)

    def test_aggregation_random_reference(self):
        rng = random.Random(6731)
        for _ in range(100):
            events = [dict(id=str(rng.randrange(60)), customer=rng.choice([' A ', 'B', 'AA', '']),
                           amount_cents=rng.randrange(-2, 10000),
                           status=rng.choice(['paid', 'refund', 'pending', 'void', 'bad']))
                      for _ in range(150)]
            first = {}
            for e in events:
                first.setdefault(e['id'], e)
            valid = [e for e in first.values() if e['customer'].strip() and
                     e['amount_cents'] >= 0 and e['status'] in main.VALID_STATUSES]
            accepted = [e for e in valid if e['status'] in ('paid', 'refund')]
            r = main.invoice(dict(events=events))
            self.assertEqual(r['duplicates'], len(events)-len(first))
            self.assertEqual(r['rejected'], len(first)-len(valid))
            self.assertEqual(r['ignored'], len(valid)-len(accepted))
            self.assertEqual(r['accepted'], len(accepted))
            self.assertEqual(r['gross_cents'], sum(e['amount_cents'] for e in accepted if e['status']=='paid'))
            self.assertEqual(r['refund_cents'], sum(e['amount_cents'] for e in accepted if e['status']=='refund'))
            for row in r['customers']:
                selected = [e for e in accepted if e['customer'].strip() == row['customer']]
                self.assertEqual(row['count'], len(selected))
                self.assertEqual(row['net_cents'], sum(e['amount_cents'] * (1 if e['status']=='paid' else -1) for e in selected))
            logs = [dict(ts_ms=rng.randrange(20), route=rng.choice([' A ', 'B', 'AA', '']),
                         status=rng.choice([200, 499, 500, 599]),
                         duration_us=rng.randrange(2**40), bytes=rng.randrange(2**40))
                    for _ in range(150)]
            selected = [e for e in logs if 5 <= e['ts_ms'] < 15]
            r = main.access_log(dict(start_ms=5, end_ms=15, events=logs))
            self.assertEqual(r['total_count'], len(selected))
            self.assertEqual(r['total_errors'], sum(e['status'] >= 500 for e in selected))
            self.assertEqual(r['total_bytes'], sum(e['bytes'] for e in selected))
            for row in r['routes']:
                group = [e for e in selected if e['route'].strip() == row['route']]
                durations = sorted(e['duration_us'] for e in group)
                self.assertEqual(row['count'], len(group))
                self.assertEqual(row['errors'], sum(e['status'] >= 500 for e in group))
                self.assertEqual(row['total_bytes'], sum(e['bytes'] for e in group))
                self.assertEqual(row['max_us'], durations[-1])
                self.assertEqual(row['p95_us'], durations[(95*len(group)-1)//100])

    def test_reused_json_codec(self):
        for line in (b'Infinity', b'-Infinity', b'NaN', b'{} trailing', b'\xef\xbb\xbf{}', b'\xff', b'{'):
            self.assertEqual(main.process_line(line), {'error': 'invalid_json'})
            self.assertEqual(main.process_line(b'  {"op":"invoice","events":[]} \r\n'),
                             main.invoice({'events': []}))

    def test_json_and_bulk_transport(self):
        a = dict(op='invoice', events=[dict(id='x', customer='A', amount_cents=2**50, status='paid')])
        b = dict(op='telemetry', samples=[-5, 2, -4], window=2, threshold=0)
        # A large valid request followed by a final line without a newline.
        large = dict(op='invoice', events=[dict(id=str(i), customer='A', amount_cents=i, status='paid') for i in range(1500)])
        charged = dict(a, fee_bps=1)
        zero = dict(a, fee_bps=0)
        requests = [a, b, a, large, charged, zero, a, charged,
                    dict(op='invoice', events=[], fee_bps=1000)] + [b]*350
        raw = b'\r\n \t\r\n{broken}\r\nNaN\n{"op":"missing"}\n"scalar"\n\xff\n'
        raw += b'\r\n'.join(json.dumps(r).encode() for r in requests)
        with tempfile.TemporaryDirectory(dir=ROOT, prefix='test_io_') as d:
            source, target = Path(d)/'input.jsonl', Path(d)/'output.jsonl'
            source.write_bytes(raw)
            result = subprocess.run([str(ROOT/'worker.sh'), str(source), str(target)], cwd='/', capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            lines = target.read_text().splitlines()
            responses = [json.loads(line) for line in lines]
            self.assertEqual(responses[:5], [{'error': 'invalid_json'}, {'error': 'invalid_json'}, {'error': 'unknown_op'}, {'error': 'unknown_op'}, {'error': 'invalid_json'}])
            self.assertEqual(responses[5:], [main.OPERATIONS[r['op']](r) for r in requests])
            self.assertEqual(responses[5], responses[7])
            self.assertEqual(responses[5]['gross_cents'], 2**50)
            self.assertTrue(target.read_bytes().endswith(b'\n'))


if __name__ == '__main__':
    unittest.main()
