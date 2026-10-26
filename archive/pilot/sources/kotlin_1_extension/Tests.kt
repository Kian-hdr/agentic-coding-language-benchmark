import java.io.File
import org.json.JSONObject

fun main() {
    var checks = 0
    fun expect(request: String, expected: String) {
        val actual = process(JSONObject(request))
        check(actual.similar(JSONObject(expected))) { "Request: $request\nExpected: $expected\nActual: $actual" }
        checks++
    }
    fun calc(expr: String, expected: String) {
        expect(JSONObject().put("op", "calc").put("expr", expr).toString(), expected)
    }
    expect("""{"op":"missing"}""", """{"error":"unknown_op"}""")
    expect("""{"op":"merge","intervals":[[4,6],[1,3],[3,4]]}""", """{"intervals":[[1,6]]}""")
    expect("""{"op":"merge","intervals":[]}""", """{"intervals":[]}""")
    expect("""{"op":"merge","intervals":[[1,2],[3,4]]}""", """{"intervals":[[1,2],[3,4]]}""")
    expect("""{"op":"merge","intervals":[[5,5]]}""", """{"intervals":[[5,5]]}""")
    expect("""{"op":"merge","intervals":[[2,3],[1,10],[1,10],[10,10],[12,13]]}""", """{"intervals":[[1,10],[12,13]]}""")
    expect("""{"op":"merge","intervals":[[-2,0],[-5,-2],[0,3],[8,9]]}""", """{"intervals":[[-5,3],[8,9]]}""")
    expect("""{"op":"merge","intervals":[[2,1]]}""", """{"error":"invalid_interval"}""")
    expect("""{"op":"merge","intervals":[[1,10],[5,4]]}""", """{"error":"invalid_interval"}""")
    expect("""{"op":"merge","intervals":[[2147483647,2147483647],[-2147483648,-2147483648]]}""", """{"intervals":[[-2147483648,-2147483648],[2147483647,2147483647]]}""")
    expect("""{"op":"merge","intervals":[[0,2147483647],[-2147483648,0]]}""", """{"intervals":[[-2147483648,2147483647]]}""")
    expect("""{"op":"ledger","entries":[]}""", """{"accounts":[],"accepted":0}""")
    expect("""{"op":"ledger","entries":[{"id":"a","account":" bank ","amount":5}]}""", """{"accounts":[{"account":"bank","balance":5,"count":1}],"accepted":1}""")
    expect("""{"op":"ledger","entries":[{"id":"a","account":"bank","amount":5},{"id":"a","account":" ","amount":100},{"id":"b","account":"bank","amount":-5},{"id":"c","account":"A","amount":2},{"id":"d","account":"a","amount":3}]}""", """{"accounts":[{"account":"A","balance":2,"count":1},{"account":"a","balance":3,"count":1},{"account":"bank","balance":0,"count":2}],"accepted":4}""")
    expect("""{"op":"ledger","entries":[{"id":"a","account":"\t\n\u000b\f\r ","amount":0}]}""", """{"error":"empty_account"}""")
    expect("""{"op":"ledger","entries":[{"id":"a","account":"\t\n\u000b\f\r bank \r\f\u000b\n\t","amount":-2147483648}]}""", """{"accounts":[{"account":"bank","balance":-2147483648,"count":1}],"accepted":1}""")
    expect("""{"op":"ledger","entries":[{"id":"a","account":"\u00a0","amount":0}]}""", """{"accounts":[{"account":"\u00a0","balance":0,"count":1}],"accepted":1}""")
    expect("""{"op":"topo","nodes":[],"edges":[]}""", """{"order":[]}""")
    expect("""{"op":"topo","nodes":["z","b","a"],"edges":[["a","b"],["a","b"]]}""", """{"order":["a","b","z"]}""")
    expect("""{"op":"topo","nodes":["b","a","A"],"edges":[]}""", """{"order":["A","a","b"]}""")
    expect("""{"op":"topo","nodes":["a"],"edges":[["a","a"]]}""", """{"error":"cycle"}""")
    expect("""{"op":"topo","nodes":["a","b","c"],"edges":[["a","b"],["b","a"]]}""", """{"error":"cycle"}""")
    expect("""{"op":"topo","nodes":["a"],"edges":[["a","a"],["a","b"]]}""", """{"error":"unknown_node"}""")
    expect("""{"op":"topo","nodes":["a"],"edges":[["b","a"]]}""", """{"error":"unknown_node"}""")
    expect("""{"op":"topo","nodes":["a","b","c","d"],"edges":[["d","b"],["c","a"],["b","a"]]}""", """{"order":["c","d","b","a"]}""")
    val values = listOf(
        "-(2 + 3) * 4 / 3" to -6,
        "2+3*4" to 14,
        "(2+3)*4" to 20,
        "20/3/2" to 3,
        "10-3-2" to 5,
        "7/-3" to -2,
        "-7/3" to -2,
        "-7/-3" to 2,
        "---++-5" to 5,
        "1--2" to 3,
        "1+-2" to -1,
        "2*-3" to -6,
        "+ ( - ( + 3 ) )" to -3,
        "000000007" to 7,
        "\t\n\u000b\u000c\r 42 \r\n" to 42,
        "2147483647" to Int.MAX_VALUE,
        "-2147483648" to Int.MIN_VALUE,
        "-2147483648/2" to -1073741824,
        "0" to 0
    )
    for ((expr, value) in values) calc(expr, """{"value":$value}""")
    val invalid = listOf("", " ", "+", "--", "()", "(1", "1)", "(1))", "((1)", "1 2", "2(3)", "(2)3", "(2)(3)", "1+", "*2", "1**2", "1//2", "1..2", "1.2", "0x10", "a", "2^3", "1,2", "1=2", "\u00a01", "１", "1\u00002")
    for (expr in invalid) calc(expr, """{"error":"syntax"}""")
    for (expr in listOf("1/0", "0/0", "3/(2-2)", "1/-0", "(4+2)/(1-1)")) {
        calc(expr, """{"error":"division_by_zero"}""")
    }
    // Deterministic arithmetic cross-checks, including signs and truncation.
    for (a in -12..12) for (b in -12..12) {
        calc("($a)+($b)*3", """{"value":${a + b * 3}}""")
        if (b != 0) calc("($a)/($b)", """{"value":${a / b}}""")
    }
    val root = File(System.getProperty("test.root"))
    val child = ProcessBuilder(File(root, "run.sh").absolutePath, File(root, "request.json").absolutePath)
        .directory(File("/private/tmp")).start()
    val stdout = child.inputStream.bufferedReader().readText()
    val stderr = child.errorStream.bufferedReader().readText()
    check(child.waitFor() == 0) { stderr }
    check(stdout.lines().filter { it.isNotEmpty() }.size == 1) { stdout }
    check(JSONObject(stdout).similar(JSONObject("""{"value":-6}"""))) { stdout }
    check(stderr.isEmpty()) { stderr }
    checks++
    println("Passed $checks checks")
}
