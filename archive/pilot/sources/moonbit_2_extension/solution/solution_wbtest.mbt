///|
fn check_response(request : String, expected : String) -> Unit raise {
  let actual = @json.parse(respond(request))
  let expected = @json.parse(expected)
  assert_eq(actual, expected)
}

///|
test "merge sorted overlaps, equal endpoints, nesting and duplicates" {
  check_response(
    "{\"op\":\"merge\",\"intervals\":[[4,6],[1,3],[3,4]]}", "{\"intervals\":[[1,6]]}",
  )
  check_response(
    "{\"op\":\"merge\",\"intervals\":[[8,9],[1,7],[2,3],[1,7],[7,7],[9,10]]}", "{\"intervals\":[[1,7],[8,10]]}",
  )
}

///|
test "merge empty, points, separated ranges and signed limits" {
  check_response("{\"op\":\"merge\",\"intervals\":[]}", "{\"intervals\":[]}")
  check_response(
    "{\"op\":\"merge\",\"intervals\":[[3,4],[1,2],[0,0],[0,0]]}", "{\"intervals\":[[0,0],[1,2],[3,4]]}",
  )
  check_response(
    "{\"op\":\"merge\",\"intervals\":[[2147483647,2147483647],[-2147483648,-1],[-1,0]]}",
    "{\"intervals\":[[-2147483648,0],[2147483647,2147483647]]}",
  )
}

///|
test "merge rejects any reversed interval" {
  check_response(
    "{\"op\":\"merge\",\"intervals\":[[1,10],[5,4]]}", "{\"error\":\"invalid_interval\"}",
  )
  check_response(
    "{\"op\":\"merge\",\"intervals\":[[2147483647,-2147483648]]}", "{\"error\":\"invalid_interval\"}",
  )
}

///|
test "ledger normalization, first id wins, zero totals, ASCII sorting" {
  check_response(
    "{\"op\":\"ledger\",\"entries\":[{\"id\":\"a\",\"account\":\" bank \",\"amount\":5},{\"id\":\"a\",\"account\":\" \",\"amount\":99},{\"id\":\"b\",\"account\":\"\\tbank\\r\\n\",\"amount\":-5},{\"id\":\"c\",\"account\":\"Zoo\",\"amount\":3},{\"id\":\"d\",\"account\":\"apple\",\"amount\":-7}]}",
    "{\"accounts\":[{\"account\":\"Zoo\",\"balance\":3,\"count\":1},{\"account\":\"apple\",\"balance\":-7,\"count\":1},{\"account\":\"bank\",\"balance\":0,\"count\":2}],\"accepted\":4}",
  )
}

///|
test "ledger empty and whitespace" {
  check_response(
    "{\"op\":\"ledger\",\"entries\":[]}", "{\"accounts\":[],\"accepted\":0}",
  )
  check_response(
    "{\"op\":\"ledger\",\"entries\":[{\"id\":\"x\",\"account\":\" \\t\\n\\r\\u000b\\u000c\",\"amount\":0}]}",
    "{\"error\":\"empty_account\"}",
  )
  // Non-ASCII whitespace must remain part of an account name.
  check_response(
    "{\"op\":\"ledger\",\"entries\":[{\"id\":\"x\",\"account\":\"\\u00a0\",\"amount\":0}]}",
    "{\"accounts\":[{\"account\":\"\\u00a0\",\"balance\":0,\"count\":1}],\"accepted\":1}",
  )
}

///|
test "topo dynamic lexicographic choice and duplicate edges" {
  check_response(
    "{\"op\":\"topo\",\"nodes\":[\"z\",\"b\",\"a\",\"c\"],\"edges\":[[\"a\",\"b\"],[\"a\",\"b\"]]}",
    "{\"order\":[\"a\",\"b\",\"c\",\"z\"]}",
  )
  check_response(
    "{\"op\":\"topo\",\"nodes\":[\"c\",\"b\",\"a\"],\"edges\":[[\"c\",\"a\"]]}",
    "{\"order\":[\"b\",\"c\",\"a\"]}",
  )
  check_response(
    "{\"op\":\"topo\",\"nodes\":[],\"edges\":[]}", "{\"order\":[]}",
  )
}

///|
test "topo cycles and unknown endpoints have priority" {
  check_response(
    "{\"op\":\"topo\",\"nodes\":[\"a\"],\"edges\":[[\"a\",\"a\"]]}", "{\"error\":\"cycle\"}",
  )
  check_response(
    "{\"op\":\"topo\",\"nodes\":[\"a\",\"b\"],\"edges\":[[\"a\",\"b\"],[\"b\",\"a\"]]}",
    "{\"error\":\"cycle\"}",
  )
  check_response(
    "{\"op\":\"topo\",\"nodes\":[\"a\"],\"edges\":[[\"a\",\"a\"],[\"missing\",\"a\"]]}",
    "{\"error\":\"unknown_node\"}",
  )
  check_response(
    "{\"op\":\"topo\",\"nodes\":[],\"edges\":[[\"a\",\"b\"]]}", "{\"error\":\"unknown_node\"}",
  )
}

///|
test "calc precedence, associativity, unary signs and signed division" {
  let cases : Array[(String, Int32)] = [
    ("-(2 + 3) * 4 / 3", -6),
    ("2+3*4", 14),
    ("20 / 3 / 2", 3),
    ("10-3-2", 5),
    ("--+-5", -5),
    ("1--2", 3),
    ("7/-3", -2),
    ("-7/3", -2),
    ("-7/-3", 2),
    ("2 * - - (3+1)", 8),
    ("00012 + 0", 12),
    ("2147483647", 2147483647),
    ("-2147483647-1", -2147483648),
    (" \t\n\r\u000b\u000c42 ", 42),
  ]
  for (expr, value) in cases {
    let request = Json::object({ "op": Json("calc"), "expr": Json(expr) })
    let expected = Json::object({ "value": Json(value) })
    check_response(request.stringify(), expected.stringify())
  }
}

///|
test "calc syntax rejection" {
  let cases = [
    "", " ", "()", "1+", "*1", "(1", "1)", "1 2", "2(3)", "(2)3", "1.5", "a", "2**3",
    "1//2", "+", "1 + ()", "1\u0000", "1\u00a0+2", "((1)))", "(1+2)(3)",
  ]
  for expr in cases {
    let request = Json::object({ "op": Json("calc"), "expr": Json(expr) })
    check_response(request.stringify(), "{\"error\":\"syntax\"}")
  }
}

///|
test "calc division by zero" {
  for expr in ["1/0", "7/(3-3)", "0/0", "2/-0"] {
    let request = Json::object({ "op": Json("calc"), "expr": Json(expr) })
    check_response(request.stringify(), "{\"error\":\"division_by_zero\"}")
  }
}

///|
test "unknown operation" {
  check_response("{\"op\":\"other\"}", "{\"error\":\"unknown_op\"}")
}

///|
test "topo ASCII lexicographic ordering across identifier lengths" {
  check_response(
    "{\"op\":\"topo\",\"nodes\":[\"b\",\"aa\",\"Azz\",\"a\"],\"edges\":[]}", "{\"order\":[\"Azz\",\"a\",\"aa\",\"b\"]}",
  )
}
