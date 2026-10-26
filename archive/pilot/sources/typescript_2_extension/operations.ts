type Entry = { id: string; account: string; amount: number };
type LedgerRequest = { entries: Entry[] };
type TopoRequest = { nodes: string[]; edges: [string, string][] };
type CalcRequest = { expr: string };
type MergeRequest = { intervals: [number, number][] };
type Failure = { error: string };

function merge({ intervals }: MergeRequest): { intervals: [number, number][] } | Failure {
  if (intervals.some(([start, end]) => start > end)) return { error: "invalid_interval" };
  const sorted = [...intervals].sort((a, b) => a[0] - b[0] || a[1] - b[1]);
  const merged: [number, number][] = [];
  for (const [start, end] of sorted) {
    const last = merged[merged.length - 1];
    if (last && start <= last[1]) last[1] = Math.max(last[1], end);
    else merged.push([start, end]);
  }
  return { intervals: merged };
}

// ASCII whitespace is HT, LF, VT, FF, CR, and space.
const asciiWhitespace = (c: string): boolean => c === " " || (c >= "\t" && c <= "\r");

function ledger({ entries }: LedgerRequest) {
  const seen = new Set<string>();
  const accounts = new Map<string, { account: string; balance: number; count: number }>();
  for (const entry of entries) {
    if (seen.has(entry.id)) continue;
    seen.add(entry.id);
    const account = entry.account.replace(/^[\x09-\x0d\x20]+|[\x09-\x0d\x20]+$/g, "");
    if (account === "") return { error: "empty_account" };
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

class MinHeap {
  private items: string[] = [];
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
    const first = this.items[0];
    const last = this.items.pop()!;
    if (this.items.length === 0) return first;
    let i = 0;
    while (i * 2 + 1 < this.items.length) {
      let child = i * 2 + 1;
      if (child + 1 < this.items.length && this.items[child + 1] < this.items[child]) child++;
      if (last <= this.items[child]) break;
      this.items[i] = this.items[child];
      i = child;
    }
    this.items[i] = last;
    return first;
  }
}

function topo({ nodes, edges }: TopoRequest) {
  const outgoing = new Map(nodes.map(node => [node, new Set<string>()]));
  const indegree = new Map(nodes.map(node => [node, 0]));
  for (const [from, to] of edges) {
    const targets = outgoing.get(from);
    if (!targets || !outgoing.has(to)) return { error: "unknown_node" };
    if (!targets.has(to)) {
      targets.add(to);
      indegree.set(to, indegree.get(to)! + 1);
    }
  }
  const available = new MinHeap();
  for (const node of nodes) if (indegree.get(node) === 0) available.push(node);
  const order: string[] = [];
  while (available.size > 0) {
    const node = available.pop();
    order.push(node);
    for (const next of outgoing.get(node)!) {
      const remaining = indegree.get(next)! - 1;
      indegree.set(next, remaining);
      if (remaining === 0) available.push(next);
    }
  }
  return order.length === nodes.length ? { order } : { error: "cycle" };
}

type Operator = "+" | "-" | "*" | "/" | "u+" | "u-" | "(";
const precedence = (op: Operator): number => op === "(" ? 0 : op === "+" || op === "-" ? 1 : op === "*" || op === "/" ? 2 : 3;

function calc({ expr }: CalcRequest): { value: number } | Failure {
  const values: number[] = [];
  const operators: Operator[] = [];
  let error: string | undefined;
  const apply = (): void => {
    const op = operators.pop()!;
    const right = values.pop()!;
    if (op === "u+" || op === "u-") {
      values.push(op === "u-" ? -right : right);
      return;
    }
    const left = values.pop()!;
    if (op === "/" && right === 0) { error = "division_by_zero"; return; }
    values.push(op === "+" ? left + right : op === "-" ? left - right : op === "*" ? left * right : Math.trunc(left / right));
  };
  let expectingOperand = true;
  for (let i = 0; i < expr.length;) {
    const c = expr[i];
    if (asciiWhitespace(c)) { i++; continue; }
    if (c >= "0" && c <= "9") {
      if (!expectingOperand) return { error: "syntax" };
      const start = i++;
      while (i < expr.length && expr[i] >= "0" && expr[i] <= "9") i++;
      values.push(Number(expr.slice(start, i)));
      expectingOperand = false;
      continue;
    }
    i++;
    if (c === "(") {
      if (!expectingOperand) return { error: "syntax" };
      operators.push("(");
    } else if (c === ")") {
      if (expectingOperand) return { error: "syntax" };
      while (operators.length && operators[operators.length - 1] !== "(") {
        apply();
        if (error) return { error };
      }
      if (operators.pop() !== "(") return { error: "syntax" };
      expectingOperand = false;
    } else if (c === "+" || c === "-" || c === "*" || c === "/") {
      if (expectingOperand) {
        if (c !== "+" && c !== "-") return { error: "syntax" };
        operators.push(c === "+" ? "u+" : "u-");
      } else {
        while (operators.length && precedence(operators[operators.length - 1]) >= precedence(c)) {
          apply();
          if (error) return { error };
        }
        operators.push(c);
        expectingOperand = true;
      }
    } else return { error: "syntax" };
  }
  if (expectingOperand) return { error: "syntax" };
  while (operators.length) {
    if (operators[operators.length - 1] === "(") return { error: "syntax" };
    apply();
    if (error) return { error };
  }
  return { value: values[0] };
}

export function operate(request: unknown): object {
  switch ((request as { op: string }).op) {
    case "ledger": return ledger(request as LedgerRequest);
    case "topo": return topo(request as TopoRequest);
    case "calc": return calc(request as CalcRequest);
    case "merge": return merge(request as MergeRequest);
    default: return { error: "unknown_op" };
  }
}
