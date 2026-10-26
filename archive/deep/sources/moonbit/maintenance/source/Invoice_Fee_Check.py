"""Independent invoice reference and persistent-worker regression check."""
import json
import random
import subprocess
import tempfile
from pathlib import Path

root = Path(__file__).resolve().parent
rng = random.Random(26)

def reference(req):
    seen, customers = set(), {}
    out = dict(accepted=0, duplicates=0, ignored=0, rejected=0,
               gross_cents=0, refund_cents=0, net_cents=0)
    enabled = 'fee_bps' in req
    if enabled:
        out['fee_cents'] = 0
    for event in req['events']:
        if event['id'] in seen:
            out['duplicates'] += 1
            continue
        seen.add(event['id'])
        name = event['customer'].strip(' \t\n\r\v\f')
        amount, status = event['amount_cents'], event['status']
        if not name or amount < 0 or status not in ('paid', 'refund', 'pending', 'void'):
            out['rejected'] += 1
            continue
        if status in ('pending', 'void'):
            out['ignored'] += 1
            continue
        out['accepted'] += 1
        if name not in customers:
            customers[name] = dict(customer=name, gross_cents=0, refund_cents=0,
                                   net_cents=0, count=0)
            if enabled:
                customers[name]['fee_cents'] = 0
        row = customers[name]
        row['count'] += 1
        key = 'gross_cents' if status == 'paid' else 'refund_cents'
        row[key] += amount
        out[key] += amount
        if enabled and status == 'paid':
            fee = (amount * req['fee_bps'] + 5000) // 10000
            row['fee_cents'] += fee
            out['fee_cents'] += fee
    for row in customers.values():
        row['net_cents'] = row['gross_cents'] - row['refund_cents'] - row.get('fee_cents', 0)
    out['net_cents'] = out['gross_cents'] - out['refund_cents'] - out.get('fee_cents', 0)
    out['customers'] = [customers[key] for key in sorted(customers)]
    return out

requests, expected = [], []
for i in range(400):
    req = dict(op='invoice', events=[dict(
        id=str(rng.randrange(25)), customer=rng.choice([' A ', 'aa', 'z', '', '\tB\v']),
        amount_cents=rng.choice([-1, 0, 4, 5, 49, 50, 51, 10**9, 9007199254735]),
        status=rng.choice(['paid', 'refund', 'pending', 'void', 'bad']))
        for _ in range(rng.randrange(45))])
    if i % 4:
        req['fee_bps'] = [0, 1, 333, 1000][i % 4]
    requests.append(json.dumps(req))
    expected.append(reference(req))
# Explicit zero, absent, malformed, and positive-fee requests in one process.
a = dict(op='invoice', fee_bps=1000, events=[dict(id='x', customer='A', amount_cents=5, status='paid')])
for req in [a, {**a, 'fee_bps': 0}, {'op': 'invoice', 'events': a['events']}, a]:
    requests.extend(['{broken', json.dumps(req)])
    expected.extend([{'error': 'invalid_json'}, reference(req)])
with tempfile.TemporaryDirectory(prefix='Invoice_Fee_') as folder:
    input_path, output_path = Path(folder) / 'Input.jsonl', Path(folder) / 'Output.jsonl'
    input_path.write_text('\r\n \t\r\n'.join(requests))
    subprocess.run([str(root / 'worker.sh'), str(input_path), str(output_path)], cwd='/private/tmp', check=True)
    actual = [json.loads(line) for line in output_path.read_text().splitlines()]
    assert len(actual) == len(expected)
    for i, (got, want) in enumerate(zip(actual, expected)):
        assert got == want, (i, got, want)
print(f'{len(expected)} persistent-worker responses matched independent reference')
