import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { writeFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { evaluate } from './main.js';

let checks = 0;
function check(input: Parameters<typeof evaluate>[0], expected: unknown): void {
  assert.deepEqual(evaluate(input), expected, JSON.stringify(input));
  checks++;
}

check({ op: 'unknown' }, { error: 'unknown_op' });
check({ op: 'merge', intervals: [[4, 6], [1, 3], [3, 4]] }, { intervals: [[1, 6]] });
check({ op: 'merge', intervals: [] }, { intervals: [] });
check({ op: 'merge', intervals: [[3, 4], [1, 2]] }, { intervals: [[1, 2], [3, 4]] });
check({ op: 'merge', intervals: [[1, 10], [2, 3], [1, 10], [10, 10], [10, 12]] }, { intervals: [[1, 12]] });
check({ op: 'merge', intervals: [[0, 0], [-5, -2], [-2, 0], [2, 2]] }, { intervals: [[-5, 0], [2, 2]] });
check({ op: 'merge', intervals: [[2147483647, 2147483647], [-2147483648, -2147483648]] },
  { intervals: [[-2147483648, -2147483648], [2147483647, 2147483647]] });
check({ op: 'merge', intervals: [[-2147483648, 0], [0, 2147483647]] },
  { intervals: [[-2147483648, 2147483647]] });
for (const intervals of [[[2, 1]], [[0, 10], [5, 4]], [[3, 2], [0, 10]]] as [number, number][][]) {
  check({ op: 'merge', intervals }, { error: 'invalid_interval' });
}
const unchanged: [number, number][] = [[4, 6], [1, 3], [3, 4]];
check({ op: 'merge', intervals: unchanged }, { intervals: [[1, 6]] });
assert.deepEqual(unchanged, [[4, 6], [1, 3], [3, 4]]);
check({ op: 'ledger', entries: [] }, { accounts: [], accepted: 0 });
check({ op: 'ledger', entries: [
  { id: 'a', account: ' bank ', amount: 5 },
  { id: 'a', account: '', amount: 100 },
  { id: 'b', account: '\tbank\r\n', amount: -5 },
  { id: 'c', account: '\vA\f', amount: 7 },
  { id: 'd', account: 'a', amount: -2 },
] }, { accounts: [
  { account: 'A', balance: 7, count: 1 },
  { account: 'a', balance: -2, count: 1 },
  { account: 'bank', balance: 0, count: 2 },
], accepted: 4 });
check({ op: 'ledger', entries: [{ id: 'x', account: ' \t\r\n\v\f', amount: 0 }] }, { error: 'empty_account' });
check({ op: 'ledger', entries: [{ id: 'x', account: '\u00a0', amount: 2147483647 }] },
  { accounts: [{ account: '\u00a0', balance: 2147483647, count: 1 }], accepted: 1 });
check({ op: 'ledger', entries: [
  { id: 'toString', account: '__proto__', amount: -2147483648 },
  { id: '__proto__', account: '__proto__', amount: 1 },
] }, { accounts: [{ account: '__proto__', balance: -2147483647, count: 2 }], accepted: 2 });

check({ op: 'topo', nodes: [], edges: [] }, { order: [] });
check({ op: 'topo', nodes: ['b', 'a'], edges: [['a', 'b'], ['a', 'b']] }, { order: ['a', 'b'] });
check({ op: 'topo', nodes: ['z', 'b', 'a'], edges: [['a', 'b']] }, { order: ['a', 'b', 'z'] });
check({ op: 'topo', nodes: ['b', 'Z', 'a', 'A'], edges: [] }, { order: ['A', 'Z', 'a', 'b'] });
check({ op: 'topo', nodes: ['a'], edges: [['a', 'a']] }, { error: 'cycle' });
check({ op: 'topo', nodes: ['a', 'b'], edges: [['a', 'b'], ['b', 'a']] }, { error: 'cycle' });
check({ op: 'topo', nodes: ['a'], edges: [['a', 'a'], ['a', 'missing']] }, { error: 'unknown_node' });
check({ op: 'topo', nodes: [], edges: [['missing', 'missing']] }, { error: 'unknown_node' });
check({ op: 'topo', nodes: ['a'], edges: [['missing', 'a']] }, { error: 'unknown_node' });

const calculations: [string, number][] = [
  ['-(2 + 3) * 4 / 3', -6], ['0', 0], ['00012', 12],
  ['1+2*3', 7], ['(1+2)*3', 9], ['8/3/2', 1], ['9-3-2', 4],
  ['-7/3', -2], ['7/-3', -2], ['-7/-3', 2], ['1/-2', 0],
  ['--+-5', -5], ['2*- -3', 6], ['1--2', 3], ['1++2', 3],
  ['\t\n\v\f\r 2 + 3 \t', 5], ['+((2))', 2], ['1-(2-(3-4))', -2],
  ['2147483647', 2147483647], ['-2147483648', -2147483648],
];
for (const [expr, value] of calculations) {
  // JSON normalizes negative zero, as the executable does.
  assert.equal(JSON.stringify(evaluate({ op: 'calc', expr })), JSON.stringify({ value }), expr);
  checks++;
}
for (const expr of ['', ' ', '()', '1+', '*2', '1 2', '2(3)', '(2)3', '(2)(3)',
  '1)', '(1', '((1)', '1/**2', '1//2', '2**3', '1.5', '1e2', '0x10', 'a', '--',
  '1,2', '1%2', '2\u00a0+3', '2_000', '[1]', '2 + ()']) {
  check({ op: 'calc', expr }, { error: 'syntax' });
}
for (const expr of ['1/0', '0/0', '2/(3-3)', '1/-0', '1/(1/2)']) {
  check({ op: 'calc', expr }, { error: 'division_by_zero' });
}

// Compare the heap-based ordering with an independent scan-based algorithm.
let seed = 123456789;
function random(): number {
  seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0;
  return seed / 4294967296;
}
for (let trial = 0; trial < 200; trial++) {
  const nodes = Array.from({ length: 12 }, (_, i) => String.fromCharCode(65 + i));
  const edges: [string, string][] = [];
  for (const from of nodes) for (const to of nodes) {
    if (random() < 0.08) edges.push([from, to]);
  }
  const remaining = new Set(nodes);
  const order: string[] = [];
  while (remaining.size) {
    const next = [...remaining].sort().find(node => !edges.some(([from, to]) => to === node && remaining.has(from)));
    if (next === undefined) break;
    remaining.delete(next);
    order.push(next);
  }
  check({ op: 'topo', nodes: nodes.reverse(), edges: [...edges, ...edges] },
    remaining.size ? { error: 'cycle' } : { order });
}

const fixture = resolve('test_request.json');
writeFileSync(fixture, JSON.stringify({ op: 'calc', expr: '-(2 + 3) * 4 / 3' }));
const child = spawnSync(resolve('run.sh'), [fixture], { encoding: 'utf8' });
assert.equal(child.status, 0, child.stderr);
assert.equal(child.stderr, '');
assert.equal(child.stdout, '{"value":-6}\n');
checks++;
for (const [request, expected] of [
  [{ op: 'merge', intervals: [[4, 6], [1, 3], [3, 4]] }, { intervals: [[1, 6]] }],
  [{ op: 'merge', intervals: [[1, 2], [3, 4]] }, { intervals: [[1, 2], [3, 4]] }],
  [{ op: 'merge', intervals: [[2, 1]] }, { error: 'invalid_interval' }],
  [{ op: 'merge', intervals: [] }, { intervals: [] }],
  [{ op: 'ledger', entries: [] }, { accounts: [], accepted: 0 }],
  [{ op: 'topo', nodes: ['b', 'a'], edges: [['a', 'b']] }, { order: ['a', 'b'] }],
] as const) {
  writeFileSync(fixture, JSON.stringify(request));
  const result = spawnSync(resolve('run.sh'), [fixture], { encoding: 'utf8' });
  assert.equal(result.status, 0, result.stderr);
  assert.equal(result.stderr, '');
  assert.equal(result.stdout, JSON.stringify(expected) + '\n');
  checks++;
}
console.log(`Passed ${checks} checks.`);
