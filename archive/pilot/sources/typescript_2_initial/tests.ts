import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { operate } from "./operations.js";

let checks = 0;
function check(input: unknown, expected: object): void {
  assert.deepEqual(JSON.parse(JSON.stringify(operate(input))), expected, JSON.stringify(input));
  checks++;
}
function calc(expr: string, value: number): void { check({ op: "calc", expr }, { value }); }

check({ op: "unknown" }, { error: "unknown_op" });
check({ op: "ledger", entries: [] }, { accounts: [], accepted: 0 });
check({ op: "ledger", entries: [
  { id: "a", account: " bank ", amount: 5 },
  { id: "a", account: "\t\n ", amount: 100 },
  { id: "b", account: "bank", amount: -5 },
  { id: "c", account: "\tA\r\v\f", amount: 7 },
  { id: "d", account: "a", amount: -7 },
] }, { accounts: [
  { account: "A", balance: 7, count: 1 },
  { account: "a", balance: -7, count: 1 },
  { account: "bank", balance: 0, count: 2 },
], accepted: 4 });
check({ op: "ledger", entries: [{ id: "a", account: " \t\n\v\f\r", amount: 0 }] }, { error: "empty_account" });
check({ op: "ledger", entries: [
  { id: "__proto__", account: "__proto__", amount: 2147483647 },
  { id: "constructor", account: "\u00a0", amount: -2147483648 },
] }, { accounts: [
  { account: "__proto__", balance: 2147483647, count: 1 },
  { account: "\u00a0", balance: -2147483648, count: 1 },
], accepted: 2 });
check({ op: "topo", nodes: [], edges: [] }, { order: [] });
check({ op: "topo", nodes: ["c", "b", "a"], edges: [["a", "b"], ["a", "b"]] }, { order: ["a", "b", "c"] });
check({ op: "topo", nodes: ["z", "b", "a"], edges: [["a", "b"]] }, { order: ["a", "b", "z"] });
check({ op: "topo", nodes: ["a"], edges: [["a", "a"]] }, { error: "cycle" });
check({ op: "topo", nodes: ["a", "b"], edges: [["a", "b"], ["b", "a"]] }, { error: "cycle" });
check({ op: "topo", nodes: ["a", "b"], edges: [["a", "b"], ["b", "a"], ["x", "a"]] }, { error: "unknown_node" });
check({ op: "topo", nodes: ["a"], edges: [["a", "x"]] }, { error: "unknown_node" });
check({ op: "topo", nodes: ["__proto__", "Z", "a", "A"], edges: [] }, { order: ["A", "Z", "__proto__", "a"] });

for (const [expr, value] of [
  ["-(2 + 3) * 4 / 3", -6], ["2+3*4", 14], ["(2+3)*4", 20],
  ["8/3", 2], ["-8/3", -2], ["8/-3", -2], ["-8/-3", 2],
  ["20/3/2", 3], ["8-3-2", 3], ["1--2", 3], ["1+-2", -1],
  ["---+-5", 5], ["-(-(-2))", -2], ["2*-(-3+1)", 4],
  ["\t\n\v\f\r + 00012 ", 12], ["2147483647", 2147483647],
  ["-2147483647-1", -2147483648], ["0/-3", 0], ["1+2*(-3)", -5],
  ["(1)+(2)", 3], ["1 / + + +2", 0], ["-(+2)*-3", 6],
] as const) calc(expr, value);
for (const expr of ["", " ", "()", "( )", "1+", "*1", "/1", "1 2", "2(3)", "(2)3", "(2)(3)", "1)", "(1", "((1)", "1+()", "1+*2", "1//2", "1.2", "1e2", "0x10", "a", "2%1", "1,2", "1\u00a0+2", "-", "(1+)" ]) {
  check({ op: "calc", expr }, { error: "syntax" });
}
for (const expr of ["1/0", "0/0", "2/(3-3)", "4/-0", "1/(2/3)"]) {
  check({ op: "calc", expr }, { error: "division_by_zero" });
}
// Large inputs verify that expression nesting and unary chains use no recursion.
calc("(".repeat(20000) + "7" + ")".repeat(20000), 7);
calc("-".repeat(20001) + "7", -7);

// Compare heap selection against a simple sorted reference on deterministic graphs.
let seed = 72431;
function random(n: number): number {
  seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0;
  return seed % n;
}
for (let trial = 0; trial < 200; trial++) {
  const nodes = Array.from({ length: 1 + random(25) }, (_, i) => `n${i}`);
  const edges: [string, string][] = [];
  for (let i = 0; i < nodes.length; i++) for (let j = i + 1; j < nodes.length; j++) {
    if (random(5) === 0) edges.push([nodes[i], nodes[j]]);
  }
  const remaining = new Set(nodes);
  const order: string[] = [];
  while (remaining.size) {
    const next = [...remaining].filter(n => !edges.some(([a, b]) => b === n && remaining.has(a))).sort()[0];
    order.push(next);
    remaining.delete(next);
  }
  check({ op: "topo", nodes: [...nodes].reverse(), edges: [...edges, ...edges] }, { order });
}

// Exercise the actual executable and assert stdout contains exactly one JSON object.
const fixtureDir = mkdtempSync(join(process.cwd(), "test_requests_"));
try {
  const examples: [object, object][] = [
    [{ op: "ledger", entries: [{ id: "a", account: " bank ", amount: 5 }] }, { accounts: [{ account: "bank", balance: 5, count: 1 }], accepted: 1 }],
    [{ op: "topo", nodes: ["b", "a"], edges: [["a", "b"]] }, { order: ["a", "b"] }],
    [{ op: "calc", expr: "-(2 + 3) * 4 / 3" }, { value: -6 }],
    [{ op: "other" }, { error: "unknown_op" }],
  ];
  for (const [input, expected] of examples) {
    const path = join(fixtureDir, "request.json");
    writeFileSync(path, JSON.stringify(input));
    const stdout = execFileSync(join(process.cwd(), "run.sh"), [path], { encoding: "utf8" });
    assert.deepEqual(JSON.parse(stdout), expected);
    assert.equal(stdout.trim().split("\n").length, 1);
    checks++;
  }
} finally {
  rmSync(fixtureDir, { recursive: true });
}
console.log(`Passed ${checks} checks.`);
