use serde_json::{Value, json};
use std::collections::{BTreeMap, BTreeSet, HashSet};

fn ledger(request: &Value) -> Value {
    let mut seen = HashSet::new();
    let mut accounts: BTreeMap<&str, (i64, usize)> = BTreeMap::new();
    let mut accepted = 0;
    for entry in request["entries"].as_array().unwrap() {
        let id = entry["id"].as_str().unwrap();
        if !seen.insert(id) { continue; }
        let account = entry["account"].as_str().unwrap()
            .trim_matches(|c: char| c.is_ascii_whitespace());
        if account.is_empty() { return json!({"error": "empty_account"}); }
        let totals = accounts.entry(account).or_insert((0, 0));
        totals.0 += entry["amount"].as_i64().unwrap();
        totals.1 += 1;
        accepted += 1;
    }
    let accounts: Vec<Value> = accounts.into_iter()
        .map(|(account, (balance, count))| json!({"account":account,"balance":balance,"count":count}))
        .collect();
    json!({"accounts":accounts,"accepted":accepted})
}

fn topo(request: &Value) -> Value {
    let nodes: Vec<&str> = request["nodes"].as_array().unwrap().iter()
        .map(|v| v.as_str().unwrap()).collect();
    let indices: BTreeMap<&str, usize> = nodes.iter().enumerate()
        .map(|(i, &node)| (node, i)).collect();
    let mut edges = HashSet::new();
    let mut adjacent = vec![Vec::new(); nodes.len()];
    let mut indegree = vec![0; nodes.len()];
    for edge in request["edges"].as_array().unwrap() {
        let from = edge[0].as_str().unwrap();
        let to = edge[1].as_str().unwrap();
        let (Some(&a), Some(&b)) = (indices.get(from), indices.get(to)) else {
            return json!({"error":"unknown_node"});
        };
        if edges.insert((a, b)) {
            adjacent[a].push(b);
            indegree[b] += 1;
        }
    }
    let mut available = BTreeSet::new();
    for (i, &node) in nodes.iter().enumerate() {
        if indegree[i] == 0 { available.insert(node); }
    }
    let mut order = Vec::new();
    while let Some(node) = available.pop_first() {
        order.push(node);
        for &next in &adjacent[indices[node]] {
            indegree[next] -= 1;
            if indegree[next] == 0 { available.insert(nodes[next]); }
        }
    }
    if order.len() != nodes.len() { json!({"error":"cycle"}) }
    else { json!({"order":order}) }
}

#[derive(Debug, PartialEq)]
enum CalcError { Syntax, DivisionByZero }
type CalcResult = Result<i64, CalcError>;
struct Parser<'a> { input: &'a [u8], pos: usize }
impl Parser<'_> {
    fn skip_space(&mut self) {
        while self.pos < self.input.len() && self.input[self.pos].is_ascii_whitespace() {
            self.pos += 1;
        }
    }
    fn peek(&mut self) -> Option<u8> {
        self.skip_space();
        self.input.get(self.pos).copied()
    }
    fn expr(&mut self) -> CalcResult {
        let mut value = self.term()?;
        loop {
            let op = self.peek();
            if !matches!(op, Some(b'+') | Some(b'-')) { break; }
            self.pos += 1;
            let rhs = self.term()?;
            value = if op == Some(b'+') { value.checked_add(rhs) } else { value.checked_sub(rhs) }
                .ok_or(CalcError::Syntax)?;
        }
        Ok(value)
    }
    fn term(&mut self) -> CalcResult {
        let mut value = self.unary()?;
        loop {
            let op = self.peek();
            if !matches!(op, Some(b'*') | Some(b'/')) { break; }
            self.pos += 1;
            let rhs = self.unary()?;
            if op == Some(b'/') && rhs == 0 { return Err(CalcError::DivisionByZero); }
            value = if op == Some(b'*') { value.checked_mul(rhs) } else { value.checked_div(rhs) }
                .ok_or(CalcError::Syntax)?;
        }
        Ok(value)
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
        if negative { value.checked_neg().ok_or(CalcError::Syntax) } else { Ok(value) }
    }
    fn primary(&mut self) -> CalcResult {
        match self.peek() {
            Some(b'(') => {
                self.pos += 1;
                let value = self.expr()?;
                if self.peek() != Some(b')') { return Err(CalcError::Syntax); }
                self.pos += 1;
                Ok(value)
            }
            Some(b'0'..=b'9') => {
                let mut value = 0i64;
                while let Some(&digit @ b'0'..=b'9') = self.input.get(self.pos) {
                    value = value.checked_mul(10).and_then(|v| v.checked_add((digit - b'0') as i64))
                        .ok_or(CalcError::Syntax)?;
                    self.pos += 1;
                }
                Ok(value)
            }
            _ => Err(CalcError::Syntax),
        }
    }
}
fn calc(expression: &str) -> Value {
    let mut parser = Parser { input: expression.as_bytes(), pos: 0 };
    match parser.expr().and_then(|value| {
        if parser.peek().is_some() { Err(CalcError::Syntax) } else { Ok(value) }
    }) {
        Ok(value) => json!({"value":value}),
        Err(CalcError::Syntax) => json!({"error":"syntax"}),
        Err(CalcError::DivisionByZero) => json!({"error":"division_by_zero"}),
    }
}
fn merge(request: &Value) -> Value {
    let mut intervals = Vec::new();
    for interval in request["intervals"].as_array().unwrap() {
        let start = interval[0].as_i64().unwrap();
        let end = interval[1].as_i64().unwrap();
        if start > end { return json!({"error":"invalid_interval"}); }
        intervals.push((start, end));
    }
    intervals.sort_unstable();
    let mut merged: Vec<(i64, i64)> = Vec::new();
    for (start, end) in intervals {
        if let Some(last) = merged.last_mut() {
            if start <= last.1 {
                last.1 = last.1.max(end);
                continue;
            }
        }
        merged.push((start, end));
    }
    json!({"intervals":merged})
}

fn process(request: &Value) -> Value {
    match request["op"].as_str() {
        Some("ledger") => ledger(request),
        Some("topo") => topo(request),
        Some("calc") => calc(request["expr"].as_str().unwrap()),
        Some("merge") => merge(request),
        _ => json!({"error":"unknown_op"}),
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
    fn merge_closed_intervals() {
        for (intervals, expected) in [
            (json!([[4,6],[1,3],[3,4]]), json!([[1,6]])),
            (json!([]), json!([])),
            (json!([[3,4],[1,2]]), json!([[1,2],[3,4]])),
            (json!([[2,2],[1,5],[1,5],[3,4],[5,7]]), json!([[1,7]])),
            (json!([[0,0],[-3,-1],[-1,0],[8,8]]), json!([[-3,0],[8,8]])),
            (json!([[2147483647,2147483647],[-2147483648,-2147483648]]),
             json!([[-2147483648,-2147483648],[2147483647,2147483647]])),
        ] {
            assert_eq!(process(&json!({"op":"merge","intervals":intervals})),
                json!({"intervals":expected}));
        }
        for intervals in [json!([[2,1]]), json!([[1,6],[5,3]]),
            json!([[2147483647,-2147483648]])] {
            assert_eq!(process(&json!({"op":"merge","intervals":intervals})),
                json!({"error":"invalid_interval"}));
        }
    }
    #[test]
    fn ledger_normalization_and_duplicates() {
        assert_eq!(process(&json!({"op":"ledger","entries":[
            {"id":"a","account":" bank \t","amount":5},
            {"id":"a","account":"  ","amount":100},
            {"id":"b","account":"bank","amount":-5},
            {"id":"c","account":"A","amount":-2}
        ]})), json!({"accounts":[{"account":"A","balance":-2,"count":1},
            {"account":"bank","balance":0,"count":2}],"accepted":3}));
        assert_eq!(process(&json!({"op":"ledger","entries":[]})),json!({"accounts":[],"accepted":0}));
        assert_eq!(process(&json!({"op":"ledger","entries":[{"id":"a","account":"\r\n\t ","amount":0}]})),json!({"error":"empty_account"}));
        assert_eq!(process(&json!({"op":"ledger","entries":[{"id":"a","account":"\u{a0}","amount":1}]}))["accepted"],1);
    }
    #[test]
    fn topo_ordering_and_validation() {
        assert_eq!(process(&json!({"op":"topo","nodes":["z","b","a","c"],"edges":[["a","b"],["a","b"],["b","c"]]})),json!({"order":["a","b","c","z"]}));
        assert_eq!(process(&json!({"op":"topo","nodes":["a"],"edges":[["a","a"]]})),json!({"error":"cycle"}));
        assert_eq!(process(&json!({"op":"topo","nodes":["a"],"edges":[["a","a"],["x","a"]]})),json!({"error":"unknown_node"}));
        assert_eq!(process(&json!({"op":"topo","nodes":[],"edges":[]})),json!({"order":[]}));
        assert_eq!(process(&json!({"op":"topo","nodes":["a","b"],"edges":[["a","b"],["b","a"]]})),json!({"error":"cycle"}));
    }
    #[test]
    fn calculator_valid() {
        for (expr, value) in [("-(2 + 3) * 4 / 3",-6),("8 / 3 * 3",6),
            ("1-2-3",-4),("---+-2",2),("2*-3+10",4),("7/-3",-2),
            ("-7/3",-2),("-7/-3",2),(" \t(12 + 3)\n * 2",30),
            ("-2147483648",-2147483648),("00012",12),("1--2",3)] {
            assert_eq!(calc(expr), json!({"value":value}), "{expr}");
        }
    }
    #[test]
    fn calculator_errors() {
        for expr in ["", " ","()","1 2","2(3)","(1)2","1+","*2","(1","1)","1.0","a","1%2","+", "1 + / 2","1\u{a0}+2"] {
            assert_eq!(calc(expr),json!({"error":"syntax"}),"{expr}");
        }
        for expr in ["1/0","1/(2-2)","0/-0"] {
            assert_eq!(calc(expr),json!({"error":"division_by_zero"}),"{expr}");
        }
        assert_eq!(process(&json!({"op":"other"})),json!({"error":"unknown_op"}));
    }
}
