// Deterministic ledger, topological ordering, and integer expression evaluation.
class Operation {
    op: string,
}

class Entry {
    id: string,
    account: string,
    amount: int,
}

class LedgerRequest {
    entries: Entry[],
}

class TopoRequest {
    nodes: string[],
    edges: string[][],
}

class CalcRequest {
    expr: string,
}

class MergeRequest {
    intervals: int[][],
}

class MergeReply {
    intervals: int[][],
}

class Failure {
    error: string,
}

class Account {
    account: string,
    balance: int,
    count: int,
}

class LedgerReply {
    accounts: Account[],
    accepted: int,
}

class TopoReply {
    order: string[],
}

class CalcReply {
    value: int,
}

type Reply = Failure | LedgerReply | TopoReply | CalcReply | MergeReply;

function merge(intervals: int[][]) -> MergeReply | Failure {
    for (let interval in intervals) {
        if (interval[0] > interval[1]) {
            return Failure { error: "invalid_interval" };
        }
    }
    let sorted = intervals.slice(0, intervals.length());
    sorted.sort_by_key((interval) -> {
        interval[0]
    });
    let merged: int[][] = [];
    for (let interval in sorted) {
        if (merged.length() == 0) {
            merged.push([interval[0], interval[1]]);
        } else {
            let last = merged[merged.length() - 1];
            if (interval[0] <= last[1]) {
                if (interval[1] > last[1]) {
                    last[1] = interval[1];
                }
            } else {
                merged.push([interval[0], interval[1]]);
            }
        }
    }
    MergeReply { intervals: merged }
}

function whitespace(c: string) -> bool {
    c == " " || c == "\t" || c == "\n" || c == "\r" || c == "\u000b" || c == "\u000c"
}

function trim_ascii(s: string) -> string {
    let start = 0;
    let end = s.length();
    while (start < end && whitespace(s.at(start) ?? "")) {
        start += 1;
    }
    while (end > start && whitespace(s.at(end - 1) ?? "")) {
        end -= 1;
    }
    s.slice(start, end)
}

function ledger(entries: Entry[]) -> LedgerReply | Failure {
    let seen: map<string, bool> = {};
    let groups: map<string, Account> = {};
    let accounts: Account[] = [];
    let accepted = 0;
    for (let entry in entries) {
        if (!(seen.get(entry.id) ?? false)) {
            seen.set(entry.id, true);
            let name = trim_ascii(entry.account);
            if (name == "") {
                return Failure { error: "empty_account" };
            }
            let group = groups.get(name);
            if (group != null) {
                group.balance += entry.amount;
                group.count += 1;
            } else {
                let account = Account { account: name, balance: entry.amount, count: 1 };
                groups.set(name, account);
                accounts.push(account);
            }
            accepted += 1;
        }
    }
    accounts.sort_by_key((a) -> {
        a.account
    });
    LedgerReply { accounts: accounts, accepted: accepted }
}

function topo(nodes: string[], edges: string[][]) -> TopoReply | Failure {
    let indegree: map<string, int> = {};
    let outgoing: map<string, string[]> = {};
    for (let node in nodes) {
        indegree.set(node, 0);
        outgoing.set(node, []);
    }
    for (let edge in edges) {
        if (indegree.get(edge[0]) == null || indegree.get(edge[1]) == null) {
            return Failure { error: "unknown_node" };
        }
    }
    for (let edge in edges) {
        let destinations = outgoing.get(edge[0]) ?? [];
        if (!destinations.includes(edge[1])) {
            destinations.push(edge[1]);
            indegree.set(edge[1], (indegree.get(edge[1]) ?? 0) + 1);
        }
    }
    let sorted = nodes.slice(0, nodes.length());
    sorted.sort_by_key((n) -> {
        n
    });
    let order: string[] = [];
    let emitted: map<string, bool> = {};
    while (order.length() < nodes.length()) {
        let chosen: string? = null;
        for (let node in sorted) {
            if (!(emitted.get(node) ?? false) && (indegree.get(node) ?? 0) == 0) {
                chosen = node;
                break;
            }
        }
        if (chosen == null) {
            return Failure { error: "cycle" };
        }
        emitted.set(chosen, true);
        order.push(chosen);
        for (let dest in outgoing.get(chosen) ?? []) {
            indegree.set(dest, (indegree.get(dest) ?? 0) - 1);
        }
    }
    TopoReply { order: order }
}

class Parser {
    chars: string[],
    pos: int,
    error: string,
}

function peek(p: Parser) -> string {
    p.chars.at(p.pos) ?? ""
}

function skip_space(p: Parser) -> void {
    while (whitespace(peek(p))) {
        p.pos += 1;
    }
}

function digit(c: string) -> bool {
    c != "" && c >= "0" && c <= "9"
}

function primary(p: Parser) -> int {
    skip_space(p);
    if (peek(p) == "(") {
        p.pos += 1;
        let value = expression(p);
        skip_space(p);
        if (peek(p) != ")") {
            p.error = "syntax";
        } else {
            p.pos += 1;
        }
        return value;
    }
    if (!digit(peek(p))) {
        p.error = "syntax";
        return 0;
    }
    let value = 0;
    while (digit(peek(p))) {
        value = value * 10 + ((peek(p).code_point_at(0) ?? 48) - 48);
        p.pos += 1;
    }
    value
}

function unary(p: Parser) -> int {
    skip_space(p);
    let sign = 1;
    while (peek(p) == "+" || peek(p) == "-") {
        if (peek(p) == "-") {
            sign = 0 - sign;
        }
        p.pos += 1;
        skip_space(p);
    }
    sign * primary(p)
}

function product(p: Parser) -> int {
    let value = unary(p);
    skip_space(p);
    while (p.error == "" && (peek(p) == "*" || peek(p) == "/")) {
        let op = peek(p);
        p.pos += 1;
        let rhs = unary(p);
        if (p.error != "") {
            return 0;
        }
        if (op == "*") {
            value = value * rhs;
        } else {
            if (rhs == 0) {
                p.error = "division_by_zero";
                return 0;
            }
            value = value / rhs;
        }
        skip_space(p);
    }
    value
}

function expression(p: Parser) -> int {
    let value = product(p);
    skip_space(p);
    while (p.error == "" && (peek(p) == "+" || peek(p) == "-")) {
        let op = peek(p);
        p.pos += 1;
        let rhs = product(p);
        if (op == "+") {
            value += rhs;
        } else {
            value -= rhs;
        }
        skip_space(p);
    }
    value
}

function calc(expr: string) -> CalcReply | Failure {
    let p = Parser { chars: expr.chars(), pos: 0, error: "" };
    let value = expression(p);
    skip_space(p);
    if (p.error != "") {
        return Failure { error: p.error };
    }
    if (p.pos != p.chars.length()) {
        return Failure { error: "syntax" };
    }
    CalcReply { value: value }
}

function main(path: string) -> Reply {
    //# Read and dispatch the request inside BAML.
    let raw = baml.fs.read(path);
    let operation = baml.json.decode<Operation>(raw);
    if (operation.op == "ledger") {
        return ledger(baml.json.decode<LedgerRequest>(raw).entries);
    }
    if (operation.op == "topo") {
        let request = baml.json.decode<TopoRequest>(raw);
        return topo(request.nodes, request.edges);
    }
    if (operation.op == "calc") {
        return calc(baml.json.decode<CalcRequest>(raw).expr);
    }
    if (operation.op == "merge") {
        return merge(baml.json.decode<MergeRequest>(raw).intervals);
    }
    Failure { error: "unknown_op" }
}
