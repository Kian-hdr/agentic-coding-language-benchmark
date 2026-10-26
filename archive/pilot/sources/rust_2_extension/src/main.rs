use serde_json::{Value, json};
use std::collections::{BTreeMap, BTreeSet, HashMap, HashSet};

fn ascii_whitespace(c: u8) -> bool {
    c == b' ' || (b'\t'..=b'\r').contains(&c)
}

fn ledger(request: &Value) -> Value {
    let mut seen = HashSet::new();
    let mut accounts: BTreeMap<String, (i64, usize)> = BTreeMap::new();
    let mut accepted = 0;
    for entry in request["entries"].as_array().unwrap() {
        let id = entry["id"].as_str().unwrap();
        if !seen.insert(id) {
            continue;
        }
        let account = entry["account"].as_str().unwrap()
            .trim_matches(|c: char| c.is_ascii() && ascii_whitespace(c as u8));
        if account.is_empty() {
            return json!({"error": "empty_account"});
        }
        let item = accounts.entry(account.to_owned()).or_insert((0, 0));
        item.0 += entry["amount"].as_i64().unwrap();
        item.1 += 1;
        accepted += 1;
    }
    let accounts: Vec<Value> = accounts.into_iter().map(|(account, (balance, count))| {
        json!({"account": account, "balance": balance, "count": count})
    }).collect();
    json!({"accounts": accounts, "accepted": accepted})
}

fn topo(request: &Value) -> Value {
    let nodes: Vec<&str> = request["nodes"].as_array().unwrap().iter()
        .map(|v| v.as_str().unwrap()).collect();
    let index: HashMap<&str, usize> = nodes.iter().enumerate()
        .map(|(i, &node)| (node, i)).collect();
    let mut adjacency = vec![Vec::new(); nodes.len()];
    let mut indegree = vec![0usize; nodes.len()];
    let mut edges = HashSet::new();
    for edge in request["edges"].as_array().unwrap() {
        let from = edge[0].as_str().unwrap();
        let to = edge[1].as_str().unwrap();
        let (Some(&a), Some(&b)) = (index.get(from), index.get(to)) else {
            return json!({"error": "unknown_node"});
        };
        if edges.insert((a, b)) {
            adjacency[a].push(b);
            indegree[b] += 1;
        }
    }
    let mut available = BTreeSet::new();
    for (i, &degree) in indegree.iter().enumerate() {
        if degree == 0 {
            available.insert(nodes[i]);
        }
    }
    let mut order = Vec::new();
    while let Some(node) = available.pop_first() {
        order.push(node);
        for &next in &adjacency[index[node]] {
            indegree[next] -= 1;
            if indegree[next] == 0 {
                available.insert(nodes[next]);
            }
        }
    }
    if order.len() == nodes.len() {
        json!({"order": order})
    } else {
        json!({"error": "cycle"})
    }
}

struct Parser<'a> {
    text: &'a [u8],
    pos: usize,
}

type CalcResult = Result<i64, &'static str>;

impl Parser<'_> {
    fn whitespace(&mut self) {
        while self.pos < self.text.len() && ascii_whitespace(self.text[self.pos]) {
            self.pos += 1;
        }
    }

    fn peek(&mut self) -> Option<u8> {
        self.whitespace();
        self.text.get(self.pos).copied()
    }

    fn expression(&mut self) -> CalcResult {
        let mut value = self.term()?;
        loop {
            match self.peek() {
                Some(b'+') => { self.pos += 1; value += self.term()?; }
                Some(b'-') => { self.pos += 1; value -= self.term()?; }
                _ => return Ok(value),
            }
        }
    }

    fn term(&mut self) -> CalcResult {
        let mut value = self.unary()?;
        loop {
            match self.peek() {
                Some(b'*') => { self.pos += 1; value *= self.unary()?; }
                Some(b'/') => {
                    self.pos += 1;
                    let divisor = self.unary()?;
                    if divisor == 0 { return Err("division_by_zero"); }
                    value /= divisor;
                }
                _ => return Ok(value),
            }
        }
    }

    fn unary(&mut self) -> CalcResult {
        let mut negative = false;
        loop {
            match self.peek() {
                Some(b'+') => self.pos += 1,
                Some(b'-') => { self.pos += 1; negative = !negative; }
                _ => break,
            }
        }
        let value = self.primary()?;
        Ok(if negative { -value } else { value })
    }

    fn primary(&mut self) -> CalcResult {
        match self.peek() {
            Some(b'(') => {
                self.pos += 1;
                let value = self.expression()?;
                if self.peek() != Some(b')') { return Err("syntax"); }
                self.pos += 1;
                Ok(value)
            }
            Some(b'0'..=b'9') => {
                let mut value = 0i64;
                while let Some(&digit @ b'0'..=b'9') = self.text.get(self.pos) {
                    value = value.checked_mul(10)
                        .and_then(|v| v.checked_add((digit - b'0') as i64))
                        .ok_or("syntax")?;
                    self.pos += 1;
                }
                Ok(value)
            }
            _ => Err("syntax"),
        }
    }
}

fn calc(expr: &str) -> Value {
    let mut parser = Parser { text: expr.as_bytes(), pos: 0 };
    match parser.expression() {
        Ok(value) if parser.peek().is_none() => json!({"value": value}),
        Ok(_) => json!({"error": "syntax"}),
        Err(error) => json!({"error": error}),
    }
}

fn merge(request: &Value) -> Value {
    let mut intervals = Vec::new();
    for interval in request["intervals"].as_array().unwrap() {
        let start = interval[0].as_i64().unwrap();
        let end = interval[1].as_i64().unwrap();
        if start > end {
            return json!({"error": "invalid_interval"});
        }
        intervals.push([start, end]);
    }
    intervals.sort_unstable();
    let mut merged: Vec<[i64; 2]> = Vec::new();
    for [start, end] in intervals {
        if let Some(last) = merged.last_mut() {
            if start <= last[1] {
                last[1] = last[1].max(end);
                continue;
            }
        }
        merged.push([start, end]);
    }
    json!({"intervals": merged})
}

fn process(request: &Value) -> Value {
    match request["op"].as_str() {
        Some("ledger") => ledger(request),
        Some("topo") => topo(request),
        Some("calc") => calc(request["expr"].as_str().unwrap()),
        Some("merge") => merge(request),
        _ => json!({"error": "unknown_op"}),
    }
}

fn main() {
    let text = std::env::args().nth(1).expect("JSON argument");
    let request: Value = serde_json::from_str(&text).expect("valid JSON");
    println!("{}", process(&request));
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn ledger_normalizes_deduplicates_and_retains_zero() {
        assert_eq!(process(&json!({"op":"ledger","entries":[
            {"id":"1","account":" z ","amount":5},
            {"id":"1","account":"  ","amount":100},
            {"id":"2","account":"\t z\r\n","amount":-5},
            {"id":"3","account":" A ","amount":2},
            {"id":"4","account":"a","amount":-1}
        ]})), json!({"accounts":[
            {"account":"A","balance":2,"count":1},
            {"account":"a","balance":-1,"count":1},
            {"account":"z","balance":0,"count":2}
        ],"accepted":4}));
        assert_eq!(ledger(&json!({"entries":[]})), json!({"accounts":[],"accepted":0}));
        assert_eq!(ledger(&json!({"entries":[{"id":"a","account":"\u{b}\u{c}","amount":0}]})), json!({"error":"empty_account"}));
    }

    #[test]
    fn topological_order_uses_dynamic_lexicographic_choice() {
        assert_eq!(topo(&json!({"nodes":["z","b","a","c"],"edges":[["b","a"],["b","a"]]})), json!({"order":["b","a","c","z"]}));
        assert_eq!(topo(&json!({"nodes":[],"edges":[]})), json!({"order":[]}));
        assert_eq!(topo(&json!({"nodes":["a","b"],"edges":[["a","b"],["b","a"]]})), json!({"error":"cycle"}));
        assert_eq!(topo(&json!({"nodes":["a"],"edges":[["a","a"]]})), json!({"error":"cycle"}));
        assert_eq!(topo(&json!({"nodes":["a"],"edges":[["a","a"],["x","a"]]})), json!({"error":"unknown_node"}));
    }

    #[test]
    fn calculator_valid_expressions() {
        for (expr, expected) in [
            ("-(2 + 3) * 4 / 3", -6), ("1+2*3",7),
            ("20/3/2",3), ("10-3-2",5), ("-7/3",-2),
            ("7/-3",-2), ("-7/-3",2), ("--+-+5",-5),
            ("1--2",3), ("(1 + (2*3))",7), ("00012",12),
            ("\t\n\u{b}\u{c}\r 8 ",8), ("-2147483648",-2147483648),
        ] {
            assert_eq!(calc(expr), json!({"value":expected}), "{expr:?}");
        }
    }

    #[test]
    fn calculator_rejects_invalid_syntax() {
        for expr in ["", " ", "()", "1+", "*1", "(1", "1)", "2(3)", "(2)3", "1 2", "1.5", "a", "1%2", "+", "1/**2", "é", "1\u{a0}+2", ")("] {
            assert_eq!(calc(expr), json!({"error":"syntax"}), "{expr:?}");
        }
        for expr in ["1/0", "1/(2-2)", "0/-0"] {
            assert_eq!(calc(expr), json!({"error":"division_by_zero"}));
        }
    }

    #[test]
    fn merge_closed_intervals() {
        for (intervals, expected) in [
            (json!([[4,6],[1,3],[3,4]]), json!([[1,6]])),
            (json!([]), json!([])),
            (json!([[3,4],[1,2]]), json!([[1,2],[3,4]])),
            (json!([[1,8],[2,3],[1,8],[8,8]]), json!([[1,8]])),
            (json!([[0,0],[-3,-1],[-1,0],[5,5]]), json!([[-3,0],[5,5]])),
            (json!([[2147483647,2147483647],[-2147483648,-2147483648]]),
             json!([[-2147483648,-2147483648],[2147483647,2147483647]])),
        ] {
            assert_eq!(process(&json!({"op":"merge","intervals":intervals})),
                       json!({"intervals":expected}));
        }
        for intervals in [json!([[2,1]]), json!([[1,5],[4,3]])] {
            assert_eq!(process(&json!({"op":"merge","intervals":intervals})),
                       json!({"error":"invalid_interval"}));
        }
    }

    #[test]
    fn unknown_operation() {
        assert_eq!(process(&json!({"op":"other"})), json!({"error":"unknown_op"}));
    }
}
