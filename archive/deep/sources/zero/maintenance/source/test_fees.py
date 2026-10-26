"""Black-box regression checks; production worker remains entirely Zero."""
import json
import random
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def invoice(req):
    seen, rows = set(), {}
    totals = dict(accepted=0, duplicates=0, ignored=0, rejected=0,
                  gross_cents=0, refund_cents=0, net_cents=0)
    if 'fee_bps' in req:
        totals['fee_cents'] = 0
    for ev in req['events']:
        if ev['id'] in seen:
            totals['duplicates'] += 1
            continue
        seen.add(ev['id'])
        name = ev['customer'].strip(' \t\n\r\v\f')
        amount, status = ev['amount_cents'], ev['status']
        if not name or amount < 0 or status not in ('paid', 'refund', 'pending', 'void'):
            totals['rejected'] += 1
            continue
        if status in ('pending', 'void'):
            totals['ignored'] += 1
            continue
        totals['accepted'] += 1
        if name not in rows:
            rows[name] = dict(customer=name, count=0, gross_cents=0, refund_cents=0, net_cents=0)
            if 'fee_bps' in req:
                rows[name]['fee_cents'] = 0
        row = rows[name]
        row['count'] += 1
        field = 'gross_cents' if status == 'paid' else 'refund_cents'
        row[field] += amount
        totals[field] += amount
        if 'fee_bps' in req and status == 'paid':
            fee = (amount * req['fee_bps'] + 5000) // 10000
            row['fee_cents'] += fee
            totals['fee_cents'] += fee
    for row in [totals] + list(rows.values()):
        row['net_cents'] = row['gross_cents'] - row['refund_cents'] - row.get('fee_cents', 0)
    return dict(customers=[rows[n] for n in sorted(rows)], **totals)

def event(i, amount, status='paid', customer=' A '):
    return dict(id=str(i), amount_cents=amount, status=status, customer=customer)

cases, expected = [], []
def add(req, result=None):
    cases.append(json.dumps(req) if not isinstance(req, str) else req)
    expected.append(invoice(req) if result is None else result)

# Half-cent boundaries, per-event rounding, refunds, ignored/rejected/duplicate events.
events = [event(0, 4), event(1, 5), event(2, 5), event(3, 6),
          event(4, 100, 'refund', 'Z'), event(5, 0, customer='aa'),
          event(6, -1), event(6, 900), event(7, 50, customer=' \t'),
          event(7, 900), event(8, 300, 'pending'), event(9, 300, 'void'),
          event(10, 300, 'bad')]
for bps in [None, 0, 1000, 1, 333, 999]:
    req = dict(op='invoice', events=events)
    if bps is not None:
        req['fee_bps'] = bps
    add(req)
    add(dict(req, events=[]))
# Safe integer boundaries, including multiplication well beyond 32 bits.
for bps, amount in [(1, 9007199254735991), (1000, 9007199254735), (0, 9007199254740991)]:
    add(dict(op='invoice', fee_bps=bps, events=[event('big', amount)]))
add('{', {'error': 'invalid_json'})
add(dict(op='telemetry', samples=[-2, 5, 8, 1], window=2, threshold=3),
    dict(count=3, min=1, max=6, above=2, weighted_checksum=25))
add(dict(op='telemetry', samples=[], window=0, threshold=0), {'error': 'invalid_window'})
add(dict(op='wat'), {'error': 'unknown_op'})
add(dict(op='access_log', fee_bps=1000, start_ms=100, end_ms=200, events=[
    dict(ts_ms=120, route=' /api/orders ', status=503, duration_us=1234, bytes=20),
    dict(ts_ms=200, route='other', status=200, duration_us=1, bytes=90)]),
    dict(routes=[dict(route='/api/orders', count=1, errors=1, total_bytes=20, max_us=1234, p95_us=1234)],
         total_count=1, total_errors=1, total_bytes=20))
rng = random.Random(13)
for _ in range(120):
    evs = [event(rng.randrange(40), rng.choice([-1, 0, 5, rng.randrange(10**12)]),
                 rng.choice(['paid', 'refund', 'pending', 'void', 'bad']),
                 rng.choice(['a', 'a10', 'a2', 'Z', ' aa\t', '\v\f', ' B\r\n']))
           for _ in range(rng.randrange(90))]
    req = dict(op='invoice', events=evs)
    if rng.randrange(3):
        req['fee_bps'] = rng.randrange(1001)
    add(req)
# A/B/A on shared buffers and recovery from malformed JSON.
for idx in [2, 0, 2, 16, 2, 0]:
    cases.append(cases[idx]); expected.append(expected[idx])
# 100 KiB request spanning multiple IO chunks.
large = dict(op='invoice', fee_bps=1000, events=[event(i, i+5) for i in range(1000)])
add(large)
assert len(cases[-1]) <= 102400
with tempfile.TemporaryDirectory() as td:
    src, dst = Path(td)/'input.jsonl', Path(td)/'output.jsonl'
    src.write_bytes(('\r\n\n' + '\r\n'.join(cases)).encode())
    subprocess.run([str(ROOT/'worker.sh'), str(src), str(dst)], cwd=td, check=True)
    actual = [json.loads(line) for line in dst.read_text().splitlines()]
    assert len(actual) == len(expected), (len(actual), len(expected))
    for i, (got, want) in enumerate(zip(actual, expected)):
        assert got == want, (i, got, want)
print(f'PASS: {len(expected)} requests, legacy schema, fee arithmetic, all operations, recovery, isolation, CRLF and final unterminated line')
