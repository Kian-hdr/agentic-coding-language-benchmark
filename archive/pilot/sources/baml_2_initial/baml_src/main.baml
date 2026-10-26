// Deterministic ledger, graph ordering, and integer expression evaluation.
class Header {
    op: string,
}

class Entry {
    id: string,
    account: string,
    amount: int,
}

class LedgerRequest {
    op: string,
    entries: Entry[],
}

class TopoRequest {
    op: string,
    nodes: string[],
    edges: string[][],
}

class CalcRequest {
    op: string,
    expr: string,
}

class ErrorReply {
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

type Reply = ErrorReply | LedgerReply | TopoReply | CalcReply;

function whitespace(c: int) -> bool {
    c == 32 || (c >= 9 && c <= 13)
}

function trim_ascii(s: string) -> string {
    let a = 0;
    let z = s.length();
    while (a < z && whitespace(s.code_point_at(a) ?? -1)) {
        a += 1;
    }
    while (z > a && whitespace(s.code_point_at(z - 1) ?? -1)) {
        z -= 1;
    }
    s.slice(a, z)
}

function ledger(entries: Entry[]) -> Reply {
    let seen: map<string, bool> = {};
    let groups: map<string, Account> = {};
    let accounts: Account[] = [];
    let accepted = 0;
    for (let entry in entries) {
        if (!(seen.get(entry.id) ?? false)) {
            seen.set(entry.id, true);
            let name = trim_ascii(entry.account);
            if (name == "") {
                return ErrorReply { error: "empty_account" };
            }
            let existing = groups.get(name);
            if (existing != null) {
                existing.balance += entry.amount;
                existing.count += 1;
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

function topo(nodes: string[], edges: string[][]) -> Reply {
    let degree: map<string, int> = {};
    let outgoing: map<string, string[]> = {};
    for (let node in nodes) {
        degree.set(node, 0);
        outgoing.set(node, []);
    }
    //# Validate every endpoint before attempting graph ordering.
    for (let edge in edges) {
        if (degree.get(edge[0]) == null || degree.get(edge[1]) == null) {
            return ErrorReply { error: "unknown_node" };
        }
        let targets = outgoing.get(edge[0]) ?? [];
        if (!targets.includes(edge[1])) {
            targets.push(edge[1]);
            degree.set(edge[1], (degree.get(edge[1]) ?? 0) + 1);
        }
    }
    let sorted = nodes.slice(0, nodes.length()).sort_by_key((n) -> {
        n
    });
    let used: map<string, bool> = {};
    let order: string[] = [];
    while (order.length() < nodes.length()) {
        let chosen: string? = null;
        for (let node in sorted) {
            if (!(used.get(node) ?? false) && degree.get(node) == 0) {
                chosen = node;
                break;
            }
        }
        if (chosen == null) {
            return ErrorReply { error: "cycle" };
        }
        used.set(chosen, true);
        order.push(chosen);
        for (let target in (outgoing.get(chosen) ?? [])) {
            degree.set(target, (degree.get(target) ?? 0) - 1);
        }
    }
    TopoReply { order: order }
}

class Parser {
    chars: int[],
    pos: int,
    error: string,
}

function skip_space(p: Parser) -> void {
    while (p.pos < p.chars.length() && whitespace(p.chars[p.pos])) {
        p.pos += 1;
    }
}

function peek(p: Parser) -> int {
    skip_space(p);
    p.chars.at(p.pos) ?? -1
}

function atom(p: Parser) -> int {
    let c = peek(p);
    if (c == 40) {
        p.pos += 1;
        let value = expression(p);
        if (peek(p) != 41) {
            p.error = "syntax";
        } else {
            p.pos += 1;
        }
        return value;
    }
    if (c < 48 || c > 57) {
        p.error = "syntax";
        return 0;
    }
    let value = 0;
    while (p.pos < p.chars.length()) {
        let digit = p.chars[p.pos];
        if (digit < 48 || digit > 57) {
            break;
        }
        value = value * 10 + digit - 48;
        p.pos += 1;
    }
    value
}

function unary(p: Parser) -> int {
    let sign = 1;
    let c = peek(p);
    while (c == 43 || c == 45) {
        if (c == 45) {
            sign = 0 - sign;
        }
        p.pos += 1;
        c = peek(p);
    }
    sign * atom(p)
}

function product(p: Parser) -> int {
    let value = unary(p);
    let c = peek(p);
    while (p.error == "" && (c == 42 || c == 47)) {
        p.pos += 1;
        let rhs = unary(p);
        if (p.error != "") {
            return 0;
        }
        if (c == 42) {
            value *= rhs;
        } else {
            if (rhs == 0) {
                p.error = "division_by_zero";
                return 0;
            }
            value = value / rhs;
        }
        c = peek(p);
    }
    value
}

function expression(p: Parser) -> int {
    let value = product(p);
    let c = peek(p);
    while (p.error == "" && (c == 43 || c == 45)) {
        p.pos += 1;
        let rhs = product(p);
        if (c == 43) {
            value += rhs;
        } else {
            value -= rhs;
        }
        c = peek(p);
    }
    value
}

function calc(expr: string) -> Reply {
    let p = Parser { chars: expr.to_code_points(), pos: 0, error: "" };
    let value = expression(p);
    if (p.error != "") {
        return ErrorReply { error: p.error };
    }
    if (peek(p) != -1) {
        return ErrorReply { error: "syntax" };
    }
    CalcReply { value: value }
}

function dispatch(raw: string) -> Reply {
    let header = baml.json.decode<Header>(raw);
    if (header.op == "ledger") {
        return ledger(baml.json.decode<LedgerRequest>(raw).entries);
    }
    if (header.op == "topo") {
        let request = baml.json.decode<TopoRequest>(raw);
        return topo(request.nodes, request.edges);
    }
    if (header.op == "calc") {
        return calc(baml.json.decode<CalcRequest>(raw).expr);
    }
    ErrorReply { error: "unknown_op" }
}

function main(path: string) -> Reply {
    dispatch(baml.fs.read(path))
}
