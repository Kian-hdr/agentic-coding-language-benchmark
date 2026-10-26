///|
fn[T : @json.FromJson] decode(j : Json) -> T {
  @json.from_json(j) catch {
    _ => panic()
  }
}

///|
fn field(j : Json, key : String) -> Json {
  let m : Map[String, Json] = decode(j)
  m[key]
}

///|
fn error(name : String) -> Json {
  Json::object({ "error": Json::string(name) })
}

///|
priv struct Entry {
  id : String
  account : String
  amount : Int32
} derive(@json.FromJson)

///|
fn ledger(request : Json) -> Json {
  let entries : Array[Entry] = decode(field(request, "entries"))
  let seen : Map[String, Bool] = Map([])
  let totals : Map[String, (Int32, Int32)] = Map([])
  let names : Array[String] = []
  let mut accepted = 0
  for entry in entries {
    if seen.get(entry.id) is Some(_) {
      continue
    }
    seen[entry.id] = true
    let name = entry.account.trim(chars=" \t\n\r\u000b\u000c").to_owned()
    if name.is_empty() {
      return error("empty_account")
    }
    match totals.get(name) {
      Some((balance, count)) =>
        totals[name] = (balance + entry.amount, count + 1)
      None => {
        names.push(name)
        totals[name] = (entry.amount, 1)
      }
    }
    accepted += 1
  }
  names.sort_by(fn(a, b) { a.lexical_compare(b) })
  let accounts = names.map(fn(name) {
    let (balance, count) = totals[name]
    Json::object({
      "account": Json::string(name),
      "balance": Json(balance),
      "count": Json(count),
    })
  })
  Json::object({ "accounts": Json::array(accounts), "accepted": Json(accepted) })
}

///|
fn topo(request : Json) -> Json {
  let nodes : Array[String] = decode(field(request, "nodes"))
  let edges : Array[(String, String)] = decode(field(request, "edges"))
  let index : Map[String, Int32] = Map([])
  for i, node in nodes {
    index[node] = i
  }
  let adjacent : Array[Array[Int32]] = Array::makei(nodes.length(), _ => [])
  let indegree = Array::make(nodes.length(), 0)
  let seen : Map[(Int32, Int32), Bool] = Map([])
  for (a, b) in edges {
    match (index.get(a), index.get(b)) {
      (Some(i), Some(j)) => {
        if seen.get((i, j)) is Some(_) {
          continue
        }
        seen[(i, j)] = true
        adjacent[i].push(j)
        indegree[j] += 1
      }
      _ => return error("unknown_node")
    }
  }
  let order : Array[String] = []
  let used = Array::make(nodes.length(), false)
  for _step = 0; _step < nodes.length(); _step = _step + 1 {
    let mut best = -1
    for i, node in nodes {
      if !used[i] && indegree[i] == 0 {
        if best == -1 || node.lexical_compare(nodes[best]) < 0 {
          best = i
        }
      }
    }
    if best == -1 {
      return error("cycle")
    }
    used[best] = true
    order.push(nodes[best])
    for j in adjacent[best] {
      indegree[j] -= 1
    }
  }
  Json::object({ "order": Json(order) })
}

///|
priv suberror CalcError {
  Syntax
  DivisionByZero
}

///|
priv struct Parser {
  text : String
  mut pos : Int32
}

///|
fn whitespace(c : UInt16) -> Bool {
  c == 32 || (c >= 9 && c <= 13)
}

///|
fn Parser::skip(self : Parser) -> Unit {
  while self.pos < self.text.length() && whitespace(self.text[self.pos]) {
    self.pos += 1
  }
}

///|
fn Parser::peek(self : Parser) -> UInt16 {
  self.skip()
  if self.pos < self.text.length() {
    self.text[self.pos]
  } else {
    0
  }
}

///|
fn Parser::primary(self : Parser) -> Int32 raise CalcError {
  let c = self.peek()
  if c == 40 {
    self.pos += 1
    let value = self.expression()
    if self.peek() != 41 {
      raise Syntax
    }
    self.pos += 1
    value
  } else if c >= 48 && c <= 57 {
    let mut value = 0
    while self.pos < self.text.length() {
      let digit = self.text[self.pos]
      if digit < 48 || digit > 57 {
        break
      }
      value = value * 10 + digit.to_int() - 48
      self.pos += 1
    }
    value
  } else {
    raise Syntax
  }
}

///|
fn Parser::unary(self : Parser) -> Int32 raise CalcError {
  let mut negative = false
  while true {
    let c = self.peek()
    if c == 43 || c == 45 {
      if c == 45 {
        negative = !negative
      }
      self.pos += 1
    } else {
      break
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
fn Parser::term(self : Parser) -> Int32 raise CalcError {
  let mut value = self.unary()
  while true {
    let c = self.peek()
    if c != 42 && c != 47 {
      break
    }
    self.pos += 1
    let right = self.unary()
    if c == 42 {
      value *= right
    } else {
      if right == 0 {
        raise DivisionByZero
      }
      value /= right
    }
  }
  value
}

///|
fn Parser::expression(self : Parser) -> Int32 raise CalcError {
  let mut value = self.term()
  while true {
    let c = self.peek()
    if c != 43 && c != 45 {
      break
    }
    self.pos += 1
    let right = self.term()
    if c == 43 {
      value += right
    } else {
      value -= right
    }
  }
  value
}

///|
fn calc(request : Json) -> Json {
  let parser = Parser::{ text: decode(field(request, "expr")), pos: 0, }
  try {
    let value = parser.expression()
    parser.skip()
    if parser.pos != parser.text.length() {
      raise Syntax
    }
    Json::object({ "value": Json(value) })
  } catch {
    Syntax => error("syntax")
    DivisionByZero => error("division_by_zero")
  }
}

///|
fn merge(request : Json) -> Json {
  let intervals : Array[(Int32, Int32)] = decode(field(request, "intervals"))
  for (start, end) in intervals {
    if start > end {
      return error("invalid_interval")
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
  Json::object({ "intervals": Json(merged) })
}

///|
pub fn respond(input : String) -> String {
  let request = @json.parse(input) catch { _ => panic() }
  let op : String = decode(field(request, "op"))
  let response = match op {
    "ledger" => ledger(request)
    "topo" => topo(request)
    "calc" => calc(request)
    "merge" => merge(request)
    _ => error("unknown_op")
  }
  response.stringify()
}
