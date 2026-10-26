import { readFileSync } from 'node:fs';

type Entry = { id: string; account: string; amount: number };
type Request =
  | { op: 'ledger'; entries: Entry[] }
  | { op: 'topo'; nodes: string[]; edges: [string, string][] }
  | { op: 'merge'; intervals: [number, number][] }
  | { op: 'calc'; expr: string };
type Failure = { error: string };
type Response = Failure
  | { accounts: { account: string; balance: number; count: number }[]; accepted: number }
  | { order: string[] }
  | { intervals: [number, number][] }
  | { value: number };

const asciiWhitespace = /[\x09-\x0d\x20]/;
const trimAscii = (s: string): string => s.replace(/^[\x09-\x0d\x20]+|[\x09-\x0d\x20]+$/g, '');

function ledger(entries: Entry[]): Response {
  const seen = new Set<string>();
  const accounts = new Map<string, { account: string; balance: number; count: number }>();
  for (const entry of entries) {
    if (seen.has(entry.id)) continue;
    seen.add(entry.id);
    const account = trimAscii(entry.account);
    if (account === '') return { error: 'empty_account' };
    const group = accounts.get(account) ?? { account, balance: 0, count: 0 };
    group.balance += entry.amount;
    group.count++;
    accounts.set(account, group);
  }
  return {
    accounts: [...accounts.values()].sort((a, b) => a.account < b.account ? -1 : a.account > b.account ? 1 : 0),
    accepted: seen.size,
  };
}

// A binary min heap keeps the choice of available node lexicographic.
class MinHeap {
  private readonly items: string[] = [];
  get size(): number { return this.items.length; }
  push(value: string): void {
    let i = this.items.length;
    this.items.push(value);
    while (i > 0) {
      const parent = (i - 1) >> 1;
      if (this.items[parent] <= value) break;
      this.items[i] = this.items[parent];
      i = parent;
    }
    this.items[i] = value;
  }
  pop(): string {
    const root = this.items[0];
    const last = this.items.pop()!;
    if (this.items.length > 0) {
      let i = 0;
      while (2 * i + 1 < this.items.length) {
        let child = 2 * i + 1;
        if (child + 1 < this.items.length && this.items[child + 1] < this.items[child]) child++;
        if (last <= this.items[child]) break;
        this.items[i] = this.items[child];
        i = child;
      }
      this.items[i] = last;
    }
    return root;
  }
}

function topo(nodes: string[], edges: [string, string][]): Response {
  const outgoing = new Map(nodes.map(node => [node, new Set<string>()]));
  const indegree = new Map(nodes.map(node => [node, 0]));
  for (const [from, to] of edges) {
    if (!outgoing.has(from) || !outgoing.has(to)) return { error: 'unknown_node' };
    const neighbors = outgoing.get(from)!;
    if (!neighbors.has(to)) {
      neighbors.add(to);
      indegree.set(to, indegree.get(to)! + 1);
    }
  }
  const ready = new MinHeap();
  for (const node of nodes) if (indegree.get(node) === 0) ready.push(node);
  const order: string[] = [];
  while (ready.size > 0) {
    const node = ready.pop();
    order.push(node);
    for (const neighbor of outgoing.get(node)!) {
      const degree = indegree.get(neighbor)! - 1;
      indegree.set(neighbor, degree);
      if (degree === 0) ready.push(neighbor);
    }
  }
  return order.length === nodes.length ? { order } : { error: 'cycle' };
}

function merge(intervals: [number, number][]): Response {
  if (intervals.some(([start, end]) => start > end)) return { error: 'invalid_interval' };
  const sorted = [...intervals].sort((a, b) => a[0] - b[0] || a[1] - b[1]);
  const merged: [number, number][] = [];
  for (const [start, end] of sorted) {
    const last = merged[merged.length - 1];
    if (last && start <= last[1]) last[1] = Math.max(last[1], end);
    else merged.push([start, end]);
  }
  return { intervals: merged };
}

class CalcError extends Error {}
class Parser {
  private position = 0;
  constructor(private readonly source: string) {}
  private skip(): void {
    while (this.position < this.source.length && asciiWhitespace.test(this.source[this.position])) this.position++;
  }
  private peek(): string {
    this.skip();
    return this.source[this.position] ?? '';
  }
  parse(): number {
    const value = this.expression();
    if (this.peek() !== '') throw new CalcError('syntax');
    return value;
  }
  private expression(): number {
    let value = this.term();
    while (true) {
      const token = this.peek();
      if (token !== '+' && token !== '-') return value;
      this.position++;
      const right = this.term();
      value = token === '+' ? value + right : value - right;
    }
  }
  private term(): number {
    let value = this.unary();
    while (true) {
      const token = this.peek();
      if (token !== '*' && token !== '/') return value;
      this.position++;
      const right = this.unary();
      if (token === '/' && right === 0) throw new CalcError('division_by_zero');
      value = token === '*' ? value * right : Math.trunc(value / right);
    }
  }
  private unary(): number {
    let sign = 1;
    while (this.peek() === '+' || this.peek() === '-') {
      if (this.source[this.position] === '-') sign = -sign;
      this.position++;
    }
    return sign * this.primary();
  }
  private primary(): number {
    const token = this.peek();
    if (token === '(') {
      this.position++;
      const value = this.expression();
      if (this.peek() !== ')') throw new CalcError('syntax');
      this.position++;
      return value;
    }
    if (token < '0' || token > '9' || token === '') throw new CalcError('syntax');
    const start = this.position;
    while (this.position < this.source.length && this.source[this.position] >= '0' && this.source[this.position] <= '9') this.position++;
    return Number(this.source.slice(start, this.position));
  }
}

export function evaluate(request: Request | { op: string }): Response {
  switch (request.op) {
    case 'merge': return merge((request as Extract<Request, { op: 'merge' }>).intervals);
    case 'ledger': return ledger((request as Extract<Request, { op: 'ledger' }>).entries);
    case 'topo': {
      const graph = request as Extract<Request, { op: 'topo' }>;
      return topo(graph.nodes, graph.edges);
    }
    case 'calc':
      try { return { value: new Parser((request as Extract<Request, { op: 'calc' }>).expr).parse() }; }
      catch (error) {
        if (error instanceof CalcError) return { error: error.message };
        throw error;
      }
    default: return { error: 'unknown_op' };
  }
}

if (require.main === module) {
  const request = JSON.parse(readFileSync(process.argv[2], 'utf8')) as Request;
  process.stdout.write(JSON.stringify(evaluate(request)) + '\n');
}
