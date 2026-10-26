import org.json.JSONArray
import org.json.JSONException
import org.json.JSONObject
import org.json.JSONParserConfiguration
import org.json.JSONTokener
import java.io.File

private fun asciiWhitespace(c: Char): Boolean = c == ' ' || c in '\t'..'\r'
private fun normalize(s: String): String = s.trim(::asciiWhitespace)
private fun error(code: String): JSONObject = JSONObject().put("error", code)

private class Customer {
    var gross = 0L
    var refund = 0L
    var count = 0L
}

private fun invoice(request: JSONObject): JSONObject {
    val seen = HashSet<String>()
    val customers = HashMap<String, Customer>()
    var accepted = 0L
    var duplicates = 0L
    var ignored = 0L
    var rejected = 0L
    var gross = 0L
    var refund = 0L
    val events = request.getJSONArray("events")
    for (i in 0 until events.length()) {
        val event = events.getJSONObject(i)
        if (!seen.add(event.getString("id"))) {
            duplicates++
            continue
        }
        val customer = normalize(event.getString("customer"))
        val amount = event.getLong("amount_cents")
        val status = event.getString("status")
        if (customer.isEmpty() || amount < 0 ||
            (status != "paid" && status != "refund" && status != "pending" && status != "void")) {
            rejected++
            continue
        }
        if (status == "pending" || status == "void") {
            ignored++
            continue
        }
        accepted++
        val row = customers.getOrPut(customer) { Customer() }
        row.count++
        if (status == "paid") {
            row.gross += amount
            gross += amount
        } else {
            row.refund += amount
            refund += amount
        }
    }
    val rows = JSONArray()
    for (name in customers.keys.sorted()) {
        val row = customers.getValue(name)
        rows.put(JSONObject().put("customer", name).put("gross_cents", row.gross)
            .put("refund_cents", row.refund).put("net_cents", row.gross - row.refund)
            .put("count", row.count))
    }
    return JSONObject().put("customers", rows).put("accepted", accepted)
        .put("duplicates", duplicates).put("ignored", ignored).put("rejected", rejected)
        .put("gross_cents", gross).put("refund_cents", refund).put("net_cents", gross - refund)
}

private class Route {
    var errors = 0L
    var bytes = 0L
    var durations = LongArray(16)
    var size = 0
    fun add(duration: Long) {
        if (size == durations.size) durations = durations.copyOf(size * 2)
        durations[size++] = duration
    }
}

private fun accessLog(request: JSONObject): JSONObject {
    val start = request.getLong("start_ms")
    val end = request.getLong("end_ms")
    val routes = HashMap<String, Route>()
    var count = 0L
    var errors = 0L
    var bytes = 0L
    val events = request.getJSONArray("events")
    for (i in 0 until events.length()) {
        val event = events.getJSONObject(i)
        val ts = event.getLong("ts_ms")
        if (ts < start || ts >= end) continue
        val row = routes.getOrPut(normalize(event.getString("route"))) { Route() }
        val eventBytes = event.getLong("bytes")
        count++
        bytes += eventBytes
        row.bytes += eventBytes
        if (event.getLong("status") >= 500) {
            errors++
            row.errors++
        }
        row.add(event.getLong("duration_us"))
    }
    val rows = JSONArray()
    for (name in routes.keys.sorted()) {
        val row = routes.getValue(name)
        java.util.Arrays.sort(row.durations, 0, row.size)
        val percentileIndex = ((95L * row.size + 99) / 100 - 1).toInt()
        rows.put(JSONObject().put("route", name).put("count", row.size.toLong())
            .put("errors", row.errors).put("total_bytes", row.bytes)
            .put("max_us", row.durations[row.size - 1])
            .put("p95_us", row.durations[percentileIndex]))
    }
    return JSONObject().put("routes", rows).put("total_count", count)
        .put("total_errors", errors).put("total_bytes", bytes)
}

private fun telemetry(request: JSONObject): JSONObject {
    val samples = request.getJSONArray("samples")
    val requestedWindow = request.getLong("window")
    if (requestedWindow <= 0 || requestedWindow > samples.length().toLong())
        return error("invalid_window")
    val window = requestedWindow.toInt()
    val threshold = request.getLong("threshold")
    var sum = 0L
    for (i in 0 until window) sum += samples.getLong(i)
    val count = samples.length() - window + 1
    var min = Long.MAX_VALUE
    var max = Long.MIN_VALUE
    var above = 0L
    var checksum = 0L
    for (i in 0 until count) {
        val average = sum / window
        min = minOf(min, average)
        max = maxOf(max, average)
        if (average > threshold) above++
        checksum += (i.toLong() + 1) * average
        if (i + 1 < count) {
            sum -= samples.getLong(i)
            sum += samples.getLong(i + window)
        }
    }
    return JSONObject().put("count", count.toLong()).put("min", min).put("max", max)
        .put("above", above).put("weighted_checksum", checksum)
}

private val parserConfiguration = JSONParserConfiguration().withStrictMode()
private val jsonNumber = Regex("-?(?:0|[1-9][0-9]*)(?:\\.[0-9]+)?(?:[eE][+-]?[0-9]+)?")

// org.json strict mode still accepts some non-JSON string escapes/control characters.
// Check token spelling here; the library validates the container grammar below.
private fun validJsonTokens(text: String): Boolean {
    var i = 0
    while (i < text.length) {
        when (val c = text[i]) {
            ' ', '\t', '\r', '\n', '{', '}', '[', ']', ':', ',' -> i++
            '"' -> {
                i++
                var closed = false
                while (i < text.length) {
                    val ch = text[i++]
                    if (ch < ' ') return false
                    if (ch == '"') {
                        closed = true
                        break
                    }
                    if (ch == '\\') {
                        if (i == text.length) return false
                        when (text[i++]) {
                            '"', '\\', '/', 'b', 'f', 'n', 'r', 't' -> Unit
                            'u' -> {
                                if (text.length - i < 4) return false
                                repeat(4) {
                                    val hex = text[i++]
                                    if (hex !in '0'..'9' && hex !in 'a'..'f' && hex !in 'A'..'F') return false
                                }
                            }
                            else -> return false
                        }
                    }
                }
                if (!closed) return false
            }
            else -> {
                i = when {
                    c == '-' || c in '0'..'9' -> (jsonNumber.matchAt(text, i) ?: return false).range.last + 1
                    text.startsWith("true", i) -> i + 4
                    text.startsWith("false", i) -> i + 5
                    text.startsWith("null", i) -> i + 4
                    else -> return false
                }
                if (i < text.length && text[i] !in " \t\r\n,]}:") return false
            }
        }
    }
    return true
}

fun processLine(line: String): JSONObject {
    if (!validJsonTokens(line)) return error("invalid_json")
    val request = try {
        val tokener = JSONTokener(line, parserConfiguration)
        val parsed = tokener.nextValue()
        if (tokener.nextClean() != '\u0000' || parsed !is JSONObject)
            return error("invalid_json")
        parsed
    } catch (_: JSONException) {
        return error("invalid_json")
    }
    return try {
        when (request.optString("op", "")) {
            "invoice" -> invoice(request)
            "access_log" -> accessLog(request)
            "telemetry" -> telemetry(request)
            else -> error("unknown_op")
        }
    } catch (_: JSONException) {
        error("invalid_json")
    }
}

fun main(args: Array<String>) {
    require(args.size == 2) { "Usage: worker.sh INPUT_JSONL OUTPUT_JSONL" }
    require(File(args[0]).canonicalFile != File(args[1]).canonicalFile) {
        "Input and output must be different files"
    }
    File(args[0]).bufferedReader(Charsets.UTF_8, 65536).use { input ->
        File(args[1]).bufferedWriter(Charsets.UTF_8, 65536).use { output ->
            while (true) {
                val line = input.readLine() ?: break
                if (line.all(::asciiWhitespace)) continue
                output.write(processLine(line).toString())
                output.newLine()
            }
        }
    }
}
