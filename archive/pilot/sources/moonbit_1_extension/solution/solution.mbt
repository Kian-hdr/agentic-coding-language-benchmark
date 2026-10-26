///|
fn[T : @json.FromJson] decode(j : Json) -> T {
  @json.from_json(j) catch {
    _ => panic()
  }
}

///|
fn error_response(message : String) -> Json {
  Json::object({ "error": Json::string(message) })
}

///|
priv struct Entry {
  id : String
  account : String
  amount : Int32
} derive(@json.FromJson)

///|
fn ledger(request : Map[String, Json]) -> Json {
  let entries : Array[Entry] = decode(request["entries"])
  let seen : Map[String, Bool] = Map([])
  let balances : Map[String, (Int32, Int32)] = Map([])
  let mut accepted = 0
  for entry in entries {
    if seen.contains(entry.id) {
      continue
    }
    seen[entry.id] = true
    let account = entry.account.trim(chars=" \t\n\r\u000b\u000c").to_owned()
    if account.is_empty() {
      return error_response("empty_account")
    }
    let (balance, count) = balances.get(account).unwrap_or((0, 0))
    balances[account] = (balance + entry.amount, count + 1)
    accepted += 1
  }
  let names = balances.keys().to_array()
  names.sort()
  let accounts = names.map(fn(name) {
    let (balance, count) = balances[name]
    Json::object({
      "account": Json::string(name),
      "balance": @json.to_json(balance),
      "count": @json.to_json(count),
    })
  })
  Json::object({
    "accounts": Json::array(accounts),
    "accepted": @json.to_json(accepted),
  })
}

///|
fn topo(request : Map[String, Json]) -> Json {
  let nodes : Array[String] = decode(request["nodes"])
  let edges : Array[(String, String)] = decode(request["edges"])
  let indegree : Map[String, Int32] = Map([])
  let outgoing : Map[String, Array[String]] = Map([])
  for node in nodes {
    indegree[node] = 0
    outgoing[node] = []
  }
  for edge in edges {
    let (source, target) = edge
    if !indegree.contains(source) || !indegree.contains(target) {
      return error_response("unknown_node")
    }
    let neighbors = outgoing[source]
    if !neighbors.contains(target) {
      neighbors.push(target)
      indegree[target] = indegree[target] + 1
    }
  }
  let sorted = nodes.copy()
  sorted.sort()
  let order : Array[String] = []
  let used : Map[String, Bool] = Map([])
  while order.length() < nodes.length() {
    let mut available : String? = None
    for node in sorted {
      if !used.contains(node) && indegree[node] == 0 {
        available = Some(node)
        break
      }
    }
    guard available is Some(node) else { return error_response("cycle") }
    used[node] = true
    order.push(node)
    for neighbor in outgoing[node] {
      indegree[neighbor] = indegree[neighbor] - 1
    }
  }
  Json::object({ "order": @json.to_json(order) })
}

///|
priv suberror CalcError {
  Syntax
  DivisionByZero
}

///|
priv struct Parser {
  chars : Array[Char]
  mut pos : Int32
}

///|
fn is_space(c : Char) -> Bool {
  c == ' ' ||
  c == '\t' ||
  c == '\n' ||
  c == '\r' ||
  c == '\u000b' ||
  c == '\u000c'
}

///|
fn Parser::skip(self : Parser) -> Unit {
  while self.pos < self.chars.length() && is_space(self.chars[self.pos]) {
    self.pos += 1
  }
}

///|
fn Parser::peek(self : Parser) -> Char? {
  self.skip()
  self.chars.get(self.pos)
}

///|
fn Parser::primary(self : Parser) -> Int64 raise CalcError {
  self.skip()
  if self.peek() == Some('(') {
    self.pos += 1
    let value = self.expression()
    if self.peek() != Some(')') {
      raise Syntax
    }
    self.pos += 1
    return value
  }
  let start = self.pos
  let mut value : Int64 = 0
  while self.pos < self.chars.length() {
    let c = self.chars[self.pos]
    if c < '0' || c > '9' {
      break
    }
    value = value * 10 + (c.to_int() - 48).to_int64()
    self.pos += 1
  }
  if self.pos == start {
    raise Syntax
  }
  value
}

///|
fn Parser::unary(self : Parser) -> Int64 raise CalcError {
  let mut negative = false
  while true {
    match self.peek() {
      Some('+') => self.pos += 1
      Some('-') => {
        self.pos += 1
        negative = !negative
      }
      _ => break
    }
  }
  let value = self.primary()
  if negative {
    -value
  } else {
    value
  }
}

///|
fn Parser::term(self : Parser) -> Int64 raise CalcError {
  let mut value = self.unary()
  while true {
    match self.peek() {
      Some('*') => {
        self.pos += 1
        value *= self.unary()
      }
      Some('/') => {
        self.pos += 1
        let divisor = self.unary()
        if divisor == 0 {
          raise DivisionByZero
        }
        value = value / divisor
      }
      _ => break
    }
  }
  value
}

///|
fn Parser::expression(self : Parser) -> Int64 raise CalcError {
  let mut value = self.term()
  while true {
    match self.peek() {
      Some('+') => {
        self.pos += 1
        value += self.term()
      }
      Some('-') => {
        self.pos += 1
        value -= self.term()
      }
      _ => break
    }
  }
  value
}

///|
fn calc(request : Map[String, Json]) -> Json {
  let expr : String = decode(request["expr"])
  let parser = Parser::{ chars: expr.to_array(), pos: 0, }
  try {
    let value = parser.expression()
    if parser.peek() != None {
      raise Syntax
    }
    Json::object({ "value": @json.to_json(value.to_int()) })
  } catch {
    Syntax => error_response("syntax")
    DivisionByZero => error_response("division_by_zero")
  }
}

///|
fn merge(request : Map[String, Json]) -> Json {
  let intervals : Array[(Int32, Int32)] = decode(request["intervals"])
  for (start, end) in intervals {
    if start > end {
      return error_response("invalid_interval")
    }
  }
  intervals.sort_by(fn(a, b) {
    if a.0 < b.0 {
      -1
    } else if a.0 > b.0 {
      1
    } else {
      0
    }
  })
  let merged : Array[(Int32, Int32)] = []
  for (start, end) in intervals {
    if merged.is_empty() {
      merged.push((start, end))
    } else {
      let last = merged.length() - 1
      let (previous_start, previous_end) = merged[last]
      if start <= previous_end {
        if end > previous_end {
          merged[last] = (previous_start, end)
        }
      } else {
        merged.push((start, end))
      }
    }
  }
  Json::object({ "intervals": @json.to_json(merged) })
}

///|
pub fn process(input : Json) -> Json {
  let request : Map[String, Json] = decode(input)
  let op : String = decode(request["op"])
  match op {
    "ledger" => ledger(request)
    "topo" => topo(request)
    "calc" => calc(request)
    "merge" => merge(request)
    _ => error_response("unknown_op")
  }
}
