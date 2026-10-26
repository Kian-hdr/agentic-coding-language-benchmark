import org.json.JSONObject

private var checks = 0
private fun verify(input: String, expected: String) {
    val actual = process(JSONObject(input))
    check(actual.similar(JSONObject(expected))) { "Input: $input\nExpected: $expected\nActual: $actual" }
    checks++
}
private fun calc(expression: String, expected: String) {
    verify(JSONObject().put("op", "calc").put("expr", expression).toString(), expected)
}
fun main() {
    verify("""{"op":"other"}""", """{"error":"unknown_op"}""")
    verify("""{"op":"ledger","entries":[]}""", """{"accounts":[],"accepted":0}""")
    verify("""{"op":"ledger","entries":[{"id":"a","account":" bank ","amount":5}]}""",
        """{"accounts":[{"account":"bank","balance":5,"count":1}],"accepted":1}""")
    verify("""{"op":"ledger","entries":[{"id":"a","account":"z","amount":5},{"id":"a","account":" ","amount":99},{"id":"b","account":"z","amount":-5},{"id":"c","account":" A\t\r\n\u000b\f","amount":-2}]}""",
        """{"accounts":[{"account":"A","balance":-2,"count":1},{"account":"z","balance":0,"count":2}],"accepted":3}""")
    verify("""{"op":"ledger","entries":[{"id":"a","account":" \t\n\r\f\u000b","amount":5}]}""",
        """{"error":"empty_account"}""")
    verify("""{"op":"ledger","entries":[{"id":"a","account":"\u00a0","amount":2147483647}]}""",
        """{"accounts":[{"account":"\u00a0","balance":2147483647,"count":1}],"accepted":1}""")
    verify("""{"op":"topo","nodes":[],"edges":[]}""", """{"order":[]}""")
    verify("""{"op":"topo","nodes":["z","b","a"],"edges":[["a","b"],["a","b"]]}""", """{"order":["a","b","z"]}""")
    verify("""{"op":"topo","nodes":["z","b","a"],"edges":[["b","a"]]}""", """{"order":["b","a","z"]}""")
    verify("""{"op":"topo","nodes":["a","b"],"edges":[["a","b"],["b","a"]]}""", """{"error":"cycle"}""")
    verify("""{"op":"topo","nodes":["a"],"edges":[["a","a"]]}""", """{"error":"cycle"}""")
    verify("""{"op":"topo","nodes":["a"],"edges":[["a","a"],["x","a"]]}""", """{"error":"unknown_node"}""")
    verify("""{"op":"topo","nodes":["a"],"edges":[["a","x"]]}""", """{"error":"unknown_node"}""")
    verify("""{"op":"topo","nodes":[],"edges":[["x","x"]]}""", """{"error":"unknown_node"}""")
    val examples = mapOf(
        "-(2 + 3) * 4 / 3" to -6,
        "2+3*4" to 14,
        "20/3/2" to 3,
        "20-3-2" to 15,
        "-7/3" to -2,
        "7/-3" to -2,
        "-7/-3" to 2,
        "--+-+5" to -5,
        "1--2" to 3,
        "2*-(-3+1)" to 4,
        "(1)+(2)*(3)" to 7,
        "-(-(-2))" to -2,
        "\t\n\r\u000b\u000c 42 " to 42,
        "000001" to 1,
        "-2147483648" to Int.MIN_VALUE,
        "2147483647" to Int.MAX_VALUE,
        "(-2147483648)/2" to -1073741824,
        "0-3/2" to -1,
        "1++2" to 3,
        "+(2+3)*-2" to -10
    )
    for ((expression, value) in examples) calc(expression, """{"value":$value}""")
    for (expression in listOf("", " \t", "()", "( )", "1+", "*1", "1 2", "2(3)", "(2)3", "(2)(3)", "1)", "(1", "1+()", "+", "--", "1**2", "1//2", "1.5", "abc", "2^3", "1,2", "\u00a01", "1\u0000", "((1)", ")1(")) {
        calc(expression, """{"error":"syntax"}""")
    }
    for (expression in listOf("1/0", "1/(2-2)", "1/-0", "0/0")) {
        calc(expression, """{"error":"division_by_zero"}""")
    }
    calc("(".repeat(20000) + "1" + ")".repeat(20000), """{"value":1}""")
    calc("-".repeat(20000) + "1", """{"value":1}""")
    calc("1" + "+1".repeat(20000), """{"value":20001}""")
    println("Passed $checks tests")
}
