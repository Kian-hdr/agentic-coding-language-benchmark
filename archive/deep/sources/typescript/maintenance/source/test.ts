import assert from 'node:assert/strict';
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { spawnSync } from 'node:child_process';
import { accessLog, invoice, processLine, telemetry, type InvoiceEvent } from './application.js';

assert.deepEqual(processLine('{'), { error: 'invalid_json' });
for (const line of ['null', '[]', '1', '"invoice"', '{"op":"missing"}']) {
  assert.deepEqual(processLine(line), { error: 'unknown_op' });
}
assert.deepEqual(telemetry([-2, 5, 8, 1], 2, 3),
  { count: 3, min: 1, max: 6, above: 2, weighted_checksum: 25 });
assert.deepEqual(telemetry([-5, 0, 0], 2, -2),
  { count: 2, min: -2, max: 0, above: 1, weighted_checksum: -2 });
for (const window of [-1, 0, 2]) assert.deepEqual(telemetry([1], window, 0), { error: 'invalid_window' });
assert.deepEqual(telemetry([], 1, 0), { error: 'invalid_window' });
assert.deepEqual(telemetry([9007199254740991], 1, 9007199254740990),
  { count: 1, min: 9007199254740991, max: 9007199254740991, above: 1, weighted_checksum: 9007199254740991 });
assert.deepEqual(telemetry([-9007199254740991, 0], 2, 0),
  { count: 1, min: -4503599627370495, max: -4503599627370495, above: 0, weighted_checksum: -4503599627370495 });

const events: InvoiceEvent[] = [
  { id: 'invalid-first', customer: ' \t\r\n\v\f', amount_cents: 10, status: 'paid' },
  { id: 'invalid-first', customer: 'A', amount_cents: 10, status: 'paid' },
  { id: 'p', customer: ' A ', amount_cents: 5000000000, status: 'paid' },
  { id: 'r', customer: '\tA\v', amount_cents: 5000000000, status: 'refund' },
  { id: 'p', customer: 'bad', amount_cents: -5, status: 'invalid' },
  { id: 'ignore', customer: 'B', amount_cents: 1, status: 'pending' },
  { id: 'void', customer: 'B', amount_cents: 1, status: 'void' },
  { id: 'reject', customer: 'B', amount_cents: -1, status: 'void' },
  { id: 'unknown', customer: 'B', amount_cents: 1, status: 'Paid' },
  { id: 'z', customer: 'a', amount_cents: 0, status: 'paid' },
  { id: 'aa', customer: 'AA', amount_cents: 0, status: 'refund' },
  { id: 'b', customer: 'B', amount_cents: 0, status: 'paid' }
];
assert.deepEqual(invoice(events), {
  customers: [
    { customer: 'A', gross_cents: 5000000000, refund_cents: 5000000000, net_cents: 0, count: 2 },
    { customer: 'AA', gross_cents: 0, refund_cents: 0, net_cents: 0, count: 1 },
    { customer: 'B', gross_cents: 0, refund_cents: 0, net_cents: 0, count: 1 },
    { customer: 'a', gross_cents: 0, refund_cents: 0, net_cents: 0, count: 1 }
  ], accepted: 5, duplicates: 2, ignored: 2, rejected: 3,
  gross_cents: 5000000000, refund_cents: 5000000000, net_cents: 0
});
assert.equal(invoice([{ id: 'x', customer: '\u00a0A\u00a0', amount_cents: 0, status: 'paid' }]).customers[0].customer, '\u00a0A\u00a0');
assert.deepEqual(invoice([]), { customers: [], accepted: 0, duplicates: 0, ignored: 0, rejected: 0, gross_cents: 0, refund_cents: 0, net_cents: 0 });
const legacyInvoice = invoice(events);
for (const bps of [0, 1, 500, 1000]) {
  const charged = invoice(events, bps);
  const expectedRows = legacyInvoice.customers.map(row => {
    const fee_cents = Number((BigInt(row.gross_cents) * BigInt(bps) + 5000n) / 10000n);
    return { ...row, fee_cents, net_cents: row.net_cents - fee_cents };
  });
  const fee_cents = expectedRows.reduce((sum, row) => sum + row.fee_cents, 0);
  assert.deepEqual(charged, { ...legacyInvoice, customers: expectedRows,
    fee_cents, net_cents: legacyInvoice.net_cents - fee_cents });
  assert.deepEqual(processLine(JSON.stringify({ op: 'invoice', events, fee_bps: bps })), charged);
  assert.deepEqual(invoice([], bps), { ...invoice([]), fee_cents: 0 });
}
// Round each accepted paid event independently; refunds never reverse fees.
const roundingEvents: InvoiceEvent[] = [
  { id: 'a', customer: ' A ', amount_cents: 5, status: 'paid' },
  { id: 'b', customer: 'A', amount_cents: 5, status: 'paid' },
  { id: 'c', customer: 'A', amount_cents: 4, status: 'paid' },
  { id: 'r', customer: 'A', amount_cents: 14, status: 'refund' },
  { id: 'refund-only', customer: 'B', amount_cents: 10, status: 'refund' }
];
assert.deepEqual(invoice(roundingEvents, 1000), {
  customers: [
    { customer: 'A', gross_cents: 14, refund_cents: 14, net_cents: -2, count: 4, fee_cents: 2 },
    { customer: 'B', gross_cents: 0, refund_cents: 10, net_cents: -10, count: 1, fee_cents: 0 }
  ], accepted: 5, duplicates: 0, ignored: 0, rejected: 0,
  gross_cents: 14, refund_cents: 24, net_cents: -12, fee_cents: 2
});
for (const bps of [0, 1, 7, 999, 1000]) {
  const largest = bps === 0 ? Number.MAX_SAFE_INTEGER : Math.floor((Number.MAX_SAFE_INTEGER - 5000) / bps);
  for (const amount of [0, 4, 5, 6, 4999, 5000, 5001, 5000000000, largest - 1, largest]) {
    const fee = Number((BigInt(amount) * BigInt(bps) + 5000n) / 10000n);
    const actual = invoice([{ id: 'large', customer: 'A', amount_cents: amount, status: 'paid' }], bps);
    assert.equal(actual.fee_cents, fee);
    assert.equal(actual.customers[0].fee_cents, fee);
    assert.equal(actual.net_cents, amount - fee);
  }
}
assert.deepEqual(invoice(events), legacyInvoice);
assert.deepEqual(accessLog(100, 200, [
  { ts_ms: 99, route: 'omit', status: 500, duration_us: 99, bytes: 99 },
  { ts_ms: 100, route: ' /x\t', status: 500, duration_us: 5000000000, bytes: 6000000000 },
  { ts_ms: 199, route: '/x', status: 499, duration_us: 1, bytes: 2 },
  { ts_ms: 200, route: 'omit', status: 999, duration_us: 99, bytes: 99 },
  { ts_ms: 120, route: '\v\f', status: 200, duration_us: 0, bytes: 0 }
]), { routes: [
  { route: '', count: 1, errors: 0, total_bytes: 0, max_us: 0, p95_us: 0 },
  { route: '/x', count: 2, errors: 1, total_bytes: 6000000002, max_us: 5000000000, p95_us: 5000000000 }
], total_count: 3, total_errors: 1, total_bytes: 6000000002 });
for (const n of [1, 19, 20, 21, 100, 101]) {
  const rows = Array.from({ length: n }, (_, i) => ({ ts_ms: 0, route: '/', status: 200, duration_us: n - i, bytes: 0 }));
  assert.equal(accessLog(0, 1, rows).routes[0].p95_us, Math.ceil(n * 0.95));
}
assert.deepEqual(accessLog(0, 0, []), { routes: [], total_count: 0, total_errors: 0, total_bytes: 0 });

let seed = 123456789;
function random(n: number): number { seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0; return seed % n; }
for (let trial = 0; trial < 1000; trial++) {
  const samples = Array.from({ length: 1 + random(80) }, () => random(20000001) - 10000000);
  const window = 1 + random(samples.length), threshold = random(20000001) - 10000000;
  const averages: bigint[] = [];
  for (let i = 0; i + window <= samples.length; i++) {
    averages.push(samples.slice(i, i + window).reduce((sum, value) => sum + BigInt(value), 0n) / BigInt(window));
  }
  const expected = { count: averages.length,
    min: Number(averages.reduce((a, b) => a < b ? a : b)),
    max: Number(averages.reduce((a, b) => a > b ? a : b)),
    above: averages.filter(a => a > BigInt(threshold)).length,
    weighted_checksum: Number(averages.reduce((sum, a, i) => sum + BigInt(i + 1) * a, 0n)) };
  assert.deepEqual(telemetry(samples, window, threshold), expected);
}

const root = resolve(__dirname, '..');
const directory = mkdtempSync(join(root, 'test_fixture_'));
try {
  const requests = [
    JSON.stringify({ op: 'invoice', events }),
    '{broken',
    JSON.stringify({ op: 'telemetry', samples: [-2, 5, 8, 1], window: 2, threshold: 3 }),
    JSON.stringify({ op: 'invoice', events }),
    JSON.stringify({ op: 'access_log', events: [], start_ms: 0, end_ms: 1 }),
    JSON.stringify({ op: 'telemetry', samples: Array.from({ length: 60000 }, (_, i) => i % 11 - 5), window: 73, threshold: 0 }),
    JSON.stringify({ op: 'invoice', events: roundingEvents, fee_bps: 1000 }),
    '{broken',
    JSON.stringify({ op: 'invoice', events, fee_bps: 0 }),
    JSON.stringify({ op: 'invoice', events }),
    JSON.stringify({ op: 'invoice', events: roundingEvents, fee_bps: 1000 }),
    ...Array.from({ length: 500 }, () => JSON.stringify({ op: 'invoice', events }))
  ];
  assert.ok(requests[5].length > 100 * 1024);
  const input = join(directory, 'input.jsonl'), output = join(directory, 'output.jsonl');
  writeFileSync(input, '\n \t\r\n' + requests.join('\r\n\r\n'));
  const run = spawnSync(join(root, 'worker.sh'), [input, output], { cwd: '/private/tmp', encoding: 'utf8' });
  assert.equal(run.status, 0, run.stderr);
  assert.equal(run.stdout, '');
  const actual = readFileSync(output, 'utf8').trimEnd().split('\n').map(line => JSON.parse(line) as unknown);
  assert.deepEqual(actual, requests.map(processLine));
  assert.deepEqual(actual[0], actual[9]);
  assert.deepEqual(actual[6], actual[10]);
  assert.ok(readFileSync(output).length > 65536);
  const sameFile = spawnSync(join(root, 'worker.sh'), [input, input], { encoding: 'utf8' });
  assert.equal(sameFile.status, 1);
  assert.match(sameFile.stderr, /different files/);
  console.log('PASS: invoice fees and legacy schema, operation edge cases, 1000 randomized telemetry cases, 511-request streaming batch, >100 KiB line, CRLF/blank/final lines, different-CWD launch, recovery/isolation, and same-file protection');
} finally {
  rmSync(directory, { recursive: true, force: true });
}
