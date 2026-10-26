import assert from 'node:assert/strict';
import { accessLog, telemetry, type AccessEvent } from './application.js';

let seed = 472891;
function random(n: number): number {
  seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0;
  return seed % n;
}
function checkTelemetry(samples: number[], window: number, threshold: number): void {
  const averages: bigint[] = [];
  for (let i = 0; i + window <= samples.length; i++) {
    let sum = 0n;
    for (let j = i; j < i + window; j++) sum += BigInt(samples[j]);
    averages.push(sum / BigInt(window));
  }
  assert.deepEqual(telemetry(samples, window, threshold), {
    count: averages.length,
    min: Number(averages.reduce((a, b) => a < b ? a : b)),
    max: Number(averages.reduce((a, b) => a > b ? a : b)),
    above: averages.filter(a => a > BigInt(threshold)).length,
    weighted_checksum: Number(averages.reduce((sum, a, i) => sum + BigInt(i + 1) * a, 0n))
  });
}
const max = Number.MAX_SAFE_INTEGER;
// Cancellation makes update transients unsafe even with safe window sums.
checkTelemetry([-max, max, 1, -max], 3, 0);
checkTelemetry([max, max, -max], 3, 0);
checkTelemetry([max, -max, -1, 1], 1, 0);
for (let trial = 0; trial < 3000; trial++) {
  const n = 1 + random(30);
  const samples = Array.from({ length: n }, () => {
    const magnitude = max - random(100000);
    return random(2) ? magnitude : -magnitude;
  });
  // A full window keeps output checksum within the supported integer domain.
  checkTelemetry(samples, n, random(2) ? 0 : max - random(100000));
}
for (let trial = 0; trial < 500; trial++) {
  const n = 1 + random(1000);
  const events: AccessEvent[] = Array.from({ length: n }, (_, i) => ({
    ts_ms: random(20) - 5,
    route: [' /a ', '\t/b\r', '/a', '\v\f', 'Z', 'AA'][random(6)],
    status: random(600),
    duration_us: trial % 4 === 0 ? i : trial % 4 === 1 ? n - i : random(trial % 4 === 2 ? 3 : 10000000000),
    bytes: random(10000000000)
  }));
  const selected = events.filter(e => e.ts_ms >= 0 && e.ts_ms < 10);
  const names = [...new Set(selected.map(e => e.route.replace(/^[ \t\r\n\v\f]+|[ \t\r\n\v\f]+$/g, '')))].sort();
  const routes = names.map(route => {
    const group = selected.filter(e => e.route.replace(/^[ \t\r\n\v\f]+|[ \t\r\n\v\f]+$/g, '') === route);
    const durations = group.map(e => e.duration_us).sort((a, b) => a - b);
    return { route, count: group.length, errors: group.filter(e => e.status >= 500).length,
      total_bytes: group.reduce((s, e) => s + e.bytes, 0), max_us: durations.at(-1),
      p95_us: durations[Math.ceil(group.length * 95 / 100) - 1] };
  });
  assert.deepEqual(accessLog(0, 10, events), { routes, total_count: selected.length,
    total_errors: selected.filter(e => e.status >= 500).length,
    total_bytes: selected.reduce((s, e) => s + e.bytes, 0) });
}
for (const mode of ['ascending', 'descending', 'equal', 'organ_pipe']) {
  const n = 20000;
  const events = Array.from({ length: n }, (_, i) => ({ ts_ms: 0, route: '/', status: 200,
    bytes: 0, duration_us: mode === 'ascending' ? i : mode === 'descending' ? n - i : mode === 'equal' ? 123 : Math.min(i, n - i) }));
  const expected = events.map(e => e.duration_us).sort((a, b) => a - b)[Math.ceil(n * .95) - 1];
  assert.equal(accessLog(0, 1, events).routes[0].p95_us, expected);
}
console.log('PASS: 3003 integer-boundary telemetry cases, 500 randomized grouped percentile cases, and 4 adversarial 20,000-event percentile cases');
