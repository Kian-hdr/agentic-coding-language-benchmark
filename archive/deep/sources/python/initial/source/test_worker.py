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

    def test_json_and_bulk_transport(self):
        a = dict(op='invoice', events=[dict(id='x', customer='A', amount_cents=2**50, status='paid')])
        b = dict(op='telemetry', samples=[-5, 2, -4], window=2, threshold=0)
        # A large valid request followed by a final line without a newline.
        large = dict(op='invoice', events=[dict(id=str(i), customer='A', amount_cents=i, status='paid') for i in range(1500)])
        requests = [a, b, a, large] + [b]*350
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
