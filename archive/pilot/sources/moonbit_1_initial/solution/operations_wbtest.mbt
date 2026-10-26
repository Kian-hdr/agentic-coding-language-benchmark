///|
fn check_case(request : String, expected : String) -> Unit raise {
  let actual = process(@json.parse(request))
  assert_eq(actual, @json.parse(expected))
}

///|
test "ledger normalizes, deduplicates, sorts, and keeps zero accounts" {
  check_case(
    "{\"op\":\"ledger\",\"entries\":[{\"id\":\"a\",\"account\":\" bank \",\"amount\":5},{\"id\":\"a\",\"account\":\"\",\"amount\":99},{\"id\":\"b\",\"account\":\"bank\",\"amount\":-5},{\"id\":\"c\",\"account\":\" A\\t\",\"amount\":2}]}",
    "{\"accounts\":[{\"account\":\"A\",\"balance\":2,\"count\":1},{\"account\":\"bank\",\"balance\":0,\"count\":2}],\"accepted\":3}",
  )
}

///|
test "ledger empty and empty account" {
  check_case(
    "{\"op\":\"ledger\",\"entries\":[]}", "{\"accounts\":[],\"accepted\":0}",
  )
  check_case(
    "{\"op\":\"ledger\",\"entries\":[{\"id\":\"a\",\"account\":\" \\t\\n\\r\\u000b\\u000c\",\"amount\":0}]}",
    "{\"error\":\"empty_account\"}",
  )
  check_case(
    "{\"op\":\"ledger\",\"entries\":[{\"id\":\"a\",\"account\":\"\\u00a0\",\"amount\":-2147483648}]}",
    "{\"accounts\":[{\"account\":\"\\u00a0\",\"balance\":-2147483648,\"count\":1}],\"accepted\":1}",
  )
}

///|
test "topo smallest available and duplicate edges" {
  check_case(
    "{\"op\":\"topo\",\"nodes\":[\"z\",\"b\",\"a\",\"c\"],\"edges\":[[\"a\",\"b\"],[\"a\",\"b\"],[\"b\",\"c\"]]}",
    "{\"order\":[\"a\",\"b\",\"c\",\"z\"]}",
  )
  check_case(
    "{\"op\":\"topo\",\"nodes\":[\"c\",\"b\",\"a\"],\"edges\":[[\"b\",\"a\"]]}",
    "{\"order\":[\"b\",\"a\",\"c\"]}",
  )
  check_case("{\"op\":\"topo\",\"nodes\":[],\"edges\":[]}", "{\"order\":[]}")
}

///|
test "topo errors and unknown node priority" {
  check_case(
    "{\"op\":\"topo\",\"nodes\":[\"a\",\"b\"],\"edges\":[[\"a\",\"b\"],[\"b\",\"a\"]]}",
    "{\"error\":\"cycle\"}",
  )
  check_case(
    "{\"op\":\"topo\",\"nodes\":[\"a\"],\"edges\":[[\"a\",\"a\"]]}", "{\"error\":\"cycle\"}",
  )
  check_case(
    "{\"op\":\"topo\",\"nodes\":[\"a\"],\"edges\":[[\"a\",\"a\"],[\"a\",\"x\"]]}",
    "{\"error\":\"unknown_node\"}",
  )
}

///|
fn check_calc(expr : String, value : Int32) -> Unit raise {
  let request = Json::object({
    "op": Json::string("calc"),
    "expr": Json::string(expr),
  })
  assert_eq(process(request), Json::object({ "value": @json.to_json(value) }))
}

///|
test "calc precedence, signs, parentheses, division, bounds" {
  check_calc("-(2 + 3) * 4 / 3", -6)
  check_calc("1+2*3", 7)
  check_calc("20/3/2", 3)
  check_calc("10-3-2", 5)
  check_calc("-7/3", -2)
  check_calc("7/-3", -2)
  check_calc("-7/-3", 2)
  check_calc("---+-2", 2)
  check_calc("1--2", 3)
  check_calc(" ( 1 + (+2) ) * 4 ", 12)
  check_calc("2147483647", 2147483647)
  check_calc("-2147483648", -2147483648)
  check_calc("1\u000b+\u000c2\t\r\n", 3)
  check_calc("00012", 12)
}

///|
test "calc rejects invalid syntax" {
  for
    expr in [
      "", " \t", "()", "1+", "*2", "(1", "1)", "1 2", "2(3)", "(2)3", "1.2", "0x10",
      "a", "2**3", "2//3", "--", "1,2", "1\u00a0+2", "(1)(2)", "+()",
    ] {
    assert_eq(
      process(
        Json::object({ "op": Json::string("calc"), "expr": Json::string(expr) }),
      ),
      error_response("syntax"),
    )
  }
}

///|
test "calc division by zero" {
  for expr in ["1/0", "1/(2-2)", "0/-0"] {
    assert_eq(
      process(
        Json::object({ "op": Json::string("calc"), "expr": Json::string(expr) }),
      ),
      error_response("division_by_zero"),
    )
  }
}

///|
test "unknown operation" {
  check_case("{\"op\":\"other\"}", "{\"error\":\"unknown_op\"}")
}
