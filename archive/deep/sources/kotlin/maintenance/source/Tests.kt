import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import kotlin.random.Random

private var checks = 0
private fun expect(input: String, expected: String) {
    val actual = processLine(input)
    check(actual.similar(JSONObject(expected))) { "Input: $input\nActual: $actual\nExpected: $expected" }
    checks++
}

fun main(args: Array<String>) {
    expect("""{"op":"invoice","events":[{"id":"e1","customer":" A ","amount_cents":150,"status":"paid"}]}""",
        """{"customers":[{"customer":"A","gross_cents":150,"refund_cents":0,"net_cents":150,"count":1}],"accepted":1,"duplicates":0,"ignored":0,"rejected":0,"gross_cents":150,"refund_cents":0,"net_cents":150}""")
    expect("""{"op":"access_log","start_ms":100,"end_ms":200,"events":[{"ts_ms":120,"route":" /api/orders ","status":503,"duration_us":1234,"bytes":20}]}""",
        """{"routes":[{"route":"/api/orders","count":1,"errors":1,"total_bytes":20,"max_us":1234,"p95_us":1234}],"total_count":1,"total_errors":1,"total_bytes":20}""")
    expect("""{"op":"telemetry","samples":[-2,5,8,1],"window":2,"threshold":3}""",
        """{"count":3,"min":1,"max":6,"above":2,"weighted_checksum":25}""")
    expect("""{"op":"telemetry","samples":[-5,2],"window":2,"threshold":-1}""",
        """{"count":1,"min":-1,"max":-1,"above":0,"weighted_checksum":-1}""")
    for (window in listOf(-1L, 0L, 3L, 4294967297L, 9007199254740991L))
        expect("""{"op":"telemetry","samples":[1,2],"window":$window,"threshold":0}""", """{"error":"invalid_window"}""")
    expect("""{"op":"telemetry","samples":[],"window":1,"threshold":0}""", """{"error":"invalid_window"}""")
    expect("""{"op":"invoice","events":[]}""", """{"customers":[],"accepted":0,"duplicates":0,"ignored":0,"rejected":0,"gross_cents":0,"refund_cents":0,"net_cents":0}""")
    expect("""{"op":"access_log","start_ms":1,"end_ms":1,"events":[]}""", """{"routes":[],"total_count":0,"total_errors":0,"total_bytes":0}""")
    expect("""{"op":"other"}""", """{"error":"unknown_op"}""")
    expect("""{"op":"invoice","events":[{"id":"bad","customer":" ","amount_cents":9,"status":"paid"},{"id":"bad","customer":"A","amount_cents":10,"status":"paid"},{"id":"p","customer":" Z ","amount_cents":9007199254740991,"status":"paid"},{"id":"r","customer":"Z","amount_cents":9007199254740991,"status":"refund"},{"id":"i","customer":"A","amount_cents":0,"status":"pending"},{"id":"v","customer":"A","amount_cents":-1,"status":"void"}]}""",
        """{"customers":[{"customer":"Z","gross_cents":9007199254740991,"refund_cents":9007199254740991,"net_cents":0,"count":2}],"accepted":2,"duplicates":1,"ignored":1,"rejected":2,"gross_cents":9007199254740991,"refund_cents":9007199254740991,"net_cents":0}""")
    for (n in listOf(1, 2, 19, 20, 21, 100, 101, 10000)) {
        val events = JSONArray()
        for (duration in n downTo 1) events.put(JSONObject().put("ts_ms", 100)
            .put("route", " / ").put("status", 500).put("duration_us", duration).put("bytes", 1))
        events.put(JSONObject().put("ts_ms", 200).put("route", "/excluded").put("status", 503)
            .put("duration_us", 999).put("bytes", 999))
        val p95 = (95 * n + 99) / 100
        expect(JSONObject().put("op", "access_log").put("start_ms", 100).put("end_ms", 200)
            .put("events", events).toString(),
            """{"routes":[{"route":"/","count":$n,"errors":$n,"total_bytes":$n,"max_us":$n,"p95_us":$p95}],"total_count":$n,"total_errors":$n,"total_bytes":$n}""")
    }
    val malformed = listOf("{", "{} x", "{\"op\":\"invoice\",}", "{'op':'x'}", "{op:\"x\"}",
        "{\"op\":\"x\",\"a\":[1,]}", "{\"op\":\"x\",\"a\":[,]}",
        "{\"op\":\"x\",\"a\":01}", "{\"op\":\"x\",\"a\":+1}",
        "{\"op\":\"x\",\"a\":.1}", "{\"op\":\"x\",\"a\":1.}",
        "{\"op\":\"x\",\"a\":NaN}", "{\"op\":\"x\",\"a\":TRUE}",
        "{\"op\":\"x\",\"a\":\"bad\u0001\"}", "\u000b{\"op\":\"x\"}",
        "{\"op\":\"x\"}\u0000garbage", "{\"op\":\"x\",\"a\":\"\\'\"}")
    for (s in malformed) expect(s, """{"error":"invalid_json"}""")

    // Field order, escaped keys/values, exact exponent numbers, and deep unknown values.
    expect("""{"samples":[1e2,-2.0,3],"threshold":0,"window":2e0,"op":"telemetry"}""",
        """{"count":2,"min":0,"max":49,"above":1,"weighted_checksum":49}""")
    expect("""{"events":[{"status":"paid","amount_cents":9e9,"customer":"\u0041","id":"\u0065"}],"\u006fp":"invoice"}""",
        """{"customers":[{"customer":"A","gross_cents":9000000000,"refund_cents":0,"net_cents":9000000000,"count":1}],"accepted":1,"duplicates":0,"ignored":0,"rejected":0,"gross_cents":9000000000,"refund_cents":0,"net_cents":9000000000}""")
    expect("{\"op\":\"other\",\"extra\":" + "[".repeat(20000) + "0" + "]".repeat(20000) + "}",
        """{"error":"unknown_op"}""")
    expect("{\"op\":\"other\",\"extra\":" + "[".repeat(20000) + "0" + "]".repeat(19999) + "}",
        """{"error":"invalid_json"}""")
    expect("{\"op\":\"other\",\"extra\":\"\\u０００１\"}", """{"error":"invalid_json"}""")

    // Rounding is per accepted paid event, before aggregation; refunds never incur fees.
    val feeEvents = """[{"id":"p1","customer":" A ","amount_cents":5,"status":"paid"},{"id":"p2","customer":"A","amount_cents":5,"status":"paid"},{"id":"p3","customer":"A","amount_cents":4,"status":"paid"},{"id":"p1","customer":"A","amount_cents":1000,"status":"paid"},{"id":"r","customer":"B","amount_cents":100,"status":"refund"},{"id":"bad","customer":" ","amount_cents":100,"status":"paid"},{"id":"bad","customer":"A","amount_cents":100,"status":"paid"},{"id":"ignored","customer":"A","amount_cents":100,"status":"pending"},{"id":"void","customer":"A","amount_cents":100,"status":"void"}]"""
    expect("""{"op":"invoice","events":$feeEvents,"fee_bps":1000}""",
        """{"customers":[{"customer":"A","gross_cents":14,"refund_cents":0,"net_cents":12,"fee_cents":2,"count":3},{"customer":"B","gross_cents":0,"refund_cents":100,"net_cents":-100,"fee_cents":0,"count":1}],"accepted":4,"duplicates":2,"ignored":2,"rejected":1,"gross_cents":14,"refund_cents":100,"net_cents":-88,"fee_cents":2}""")
    expect("""{"op":"invoice","fee_bps":0,"events":[]}""",
        """{"customers":[],"accepted":0,"duplicates":0,"ignored":0,"rejected":0,"gross_cents":0,"refund_cents":0,"net_cents":0,"fee_cents":0}""")
    expect("""{"op":"invoice","fee_bps":1,"events":[{"id":"large","customer":"A","amount_cents":9007199254735991,"status":"paid"}]}""",
        """{"customers":[{"customer":"A","gross_cents":9007199254735991,"refund_cents":0,"net_cents":9006298534810517,"fee_cents":900719925474,"count":1}],"accepted":1,"duplicates":0,"ignored":0,"rejected":0,"gross_cents":9007199254735991,"refund_cents":0,"net_cents":9006298534810517,"fee_cents":900719925474}""")

    val random = Random(93882)
    repeat(400) {
        val n = random.nextInt(1, 200)
        val values = LongArray(n) { random.nextLong(-10000000000L, 10000000000L) }
        val window = random.nextInt(1, n + 1)
        val threshold = random.nextLong(-10000000000L, 10000000000L)
        val averages = (0..n-window).map { start -> (start until start+window).sumOf { values[it] } / window }
        val expected = JSONObject().put("count", averages.size).put("min", averages.min())
            .put("max", averages.max()).put("above", averages.count { it > threshold })
            .put("weighted_checksum", averages.withIndex().sumOf { (it.index + 1L) * it.value })
        expect(JSONObject().put("op", "telemetry").put("samples", JSONArray(values.toList()))
            .put("window", window).put("threshold", threshold).toString(), expected.toString())
    }
    repeat(150) {
        val names = listOf("A", "AA", "B", "Z", "a", "", "a\u0000")
        val events = JSONArray()
        val seen = mutableSetOf<String>()
        val accepted = mutableListOf<Triple<String, Long, String>>()
        var duplicate = 0
        var rejected = 0
        var ignored = 0
        repeat(250) {
            val id = "e${random.nextInt(150)}"
            val name = names.random(random)
            val amount = random.nextLong(-20, 10000000000L)
            val status = listOf("paid", "refund", "void", "pending", "bad").random(random)
            events.put(JSONObject().put("id", id).put("customer", "\u000b\t $name \u000c\r\n")
                .put("amount_cents", amount).put("status", status))
            if (!seen.add(id)) duplicate++
            else if (name.isEmpty() || amount < 0 || status == "bad") rejected++
            else if (status == "pending" || status == "void") ignored++
            else accepted.add(Triple(name, amount, status))
        }
        val rows = JSONArray()
        for ((name, group) in accepted.groupBy { it.first }.toSortedMap()) {
            val gross = group.filter { it.third == "paid" }.sumOf { it.second }
            val refund = group.filter { it.third == "refund" }.sumOf { it.second }
            rows.put(JSONObject().put("customer", name).put("gross_cents", gross)
                .put("refund_cents", refund).put("net_cents", gross-refund).put("count", group.size))
        }
        val gross = accepted.filter { it.third == "paid" }.sumOf { it.second }
        val refund = accepted.filter { it.third == "refund" }.sumOf { it.second }
        val request = JSONObject().put("op", "invoice").put("events", events)
        val expected = JSONObject().put("customers", rows).put("accepted", accepted.size)
            .put("duplicates", duplicate).put("ignored", ignored).put("rejected", rejected)
            .put("gross_cents", gross).put("refund_cents", refund).put("net_cents", gross-refund)
        expect(request.toString(), expected.toString())
        for (bps in listOf(0L, random.nextLong(1, 1001))) {
            var totalFee = 0L
            for (i in 0 until rows.length()) {
                val row = rows.getJSONObject(i)
                val fee = accepted.filter { it.first == row.getString("customer") && it.third == "paid" }
                    .sumOf { (it.second * bps + 5000L) / 10000L }
                row.put("fee_cents", fee).put("net_cents", row.getLong("gross_cents") - row.getLong("refund_cents") - fee)
                totalFee += fee
            }
            request.put("fee_bps", bps)
            expected.put("fee_cents", totalFee).put("net_cents", gross-refund-totalFee)
            expect(request.toString(), expected.toString())
        }
    }
    repeat(150) {
        val events = JSONArray()
        data class Event(val ts: Long, val route: String, val status: Long, val us: Long, val bytes: Long)
        val data = List(random.nextInt(1, 3000)) {
            Event(random.nextLong(80, 220), listOf("", "/A", "/AA", "/B", "/a").random(random),
                random.nextLong(200, 600), random.nextLong(0, 10000000000L), random.nextLong(0, 10000000000L))
        }
        for (e in data) events.put(JSONObject().put("ts_ms", e.ts).put("route", "\u000b ${e.route}\u000c")
            .put("status", e.status).put("duration_us", e.us).put("bytes", e.bytes))
        val selected = data.filter { it.ts >= 100 && it.ts < 200 }
        val rows = JSONArray()
        for ((name, group) in selected.groupBy { it.route }.toSortedMap()) {
            val durations = group.map { it.us }.sorted()
            val index = kotlin.math.ceil(0.95 * durations.size).toInt() - 1
            rows.put(JSONObject().put("route", name).put("count", group.size)
                .put("errors", group.count { it.status >= 500 }).put("total_bytes", group.sumOf { it.bytes })
                .put("max_us", durations.last()).put("p95_us", durations[index]))
        }
        expect(JSONObject().put("op", "access_log").put("start_ms", 100).put("end_ms", 200)
            .put("events", events).toString(), JSONObject().put("routes", rows).put("total_count", selected.size)
            .put("total_errors", selected.count { it.status >= 500 }).put("total_bytes", selected.sumOf { it.bytes }).toString())
    }
    val base = File(args[0]).canonicalFile
    val testDir = File(base, "test_artifacts").apply { mkdirs() }
    val input = File(testDir, "input.jsonl")
    val output = File(testDir, "output.jsonl")
    val a = """{"op":"telemetry","samples":[9007199254740991],"window":1,"threshold":0}"""
    val large = JSONObject().put("op", "telemetry").put("window", 500).put("threshold", 0)
        .put("samples", JSONArray(List(45000) { if (it % 2 == 0) 1 else -1 })).toString()
    check(large.length > 100 * 1024)
    val legacyInvoice = """{"op":"invoice","events":$feeEvents}"""
    val feeInvoice = """{"op":"invoice","fee_bps":1000,"events":$feeEvents}"""
    val zeroInvoice = """{"op":"invoice","fee_bps":0,"events":$feeEvents}"""
    val records = listOf(a, "{", "{\"op\":\"other\"}", large, a, legacyInvoice, feeInvoice, "{", zeroInvoice, legacyInvoice, feeInvoice) + List(600) { a }
    input.bufferedWriter().use { writer ->
        writer.write("\n \t\r\n")
        records.forEachIndexed { index, record ->
            writer.write(record)
            if (index != records.lastIndex) writer.write(if (index % 2 == 0) "\r\n" else "\n")
        }
    }
    val process = ProcessBuilder(File(base, "worker.sh").path, input.path, output.path)
        .directory(testDir).redirectError(ProcessBuilder.Redirect.INHERIT).start()
    check(process.waitFor() == 0)
    val lines = output.readLines()
    check(lines.size == records.size)
    lines.forEachIndexed { index, line -> check(JSONObject(line).similar(processLine(records[index]))) }
    check(lines[0] == lines[4])
    check(lines[5] == lines[9])
    check(lines[6] == lines[10])
    checks += lines.size
    println("PASS: $checks checks; seeded reference tests, malformed JSON, >100 KiB line, ${records.size} records, CRLF/LF, final unterminated line, external working directory, A/B/A independence")
}
