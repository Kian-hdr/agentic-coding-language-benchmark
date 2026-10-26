import org.json.JSONArray
import org.json.JSONObject
import java.io.File

private fun asciiWhitespace(c: Char): Boolean = c == ' ' || c in '\t'..'\r'
private fun normalize(s: String): String = s.trim(::asciiWhitespace)
private fun error(code: String): JSONObject = JSONObject().put("error", code)

private class Customer {
    var gross = 0L
    var refund = 0L
    var count = 0L
}

private fun invoice(request: Request): JSONObject {
    val seen = HashSet<String>()
    val customers = HashMap<String, Customer>()
    var accepted = 0L
    var duplicates = 0L
    var ignored = 0L
    var rejected = 0L
    var gross = 0L
    var refund = 0L
    val events = request.cursor("events")
    events.need('[')
    if (!events.take(']')) { do {
        var id = ""
        var customer = ""
        var amount = 0L
        var status = ""
        events.need('{')
        if (!events.take('}')) {
            do {
                val key = events.string()
                events.need(':')
                when (key) {
                    "id" -> id = events.string()
                    "customer" -> customer = normalize(events.string())
                    "amount_cents" -> amount = events.long()
                    "status" -> status = events.string()
                    else -> events.skip()
                }
            } while (events.take(','))
            events.need('}')
        }
        if (!seen.add(id)) {
            duplicates++
        } else if (customer.isEmpty() || amount < 0 ||
            (status != "paid" && status != "refund" && status != "pending" && status != "void")) {
            rejected++
        } else if (status == "pending" || status == "void") {
            ignored++
        } else {
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
    } while (events.take(','))
    events.need(']')
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
    var max = 0L
    fun add(duration: Long) {
        if (size == durations.size) durations = durations.copyOf(size * 2)
        durations[size++] = duration
        if (duration > max) max = duration
    }
}

private fun accessLog(request: Request): JSONObject {
    val start = request.long("start_ms")
    val end = request.long("end_ms")
    val routes = HashMap<String, Route>()
    var count = 0L
    var errors = 0L
    var bytes = 0L
    val events = request.cursor("events")
    events.need('[')
    if (!events.take(']')) { do {
        var ts = 0L
        var route = ""
        var status = 0L
        var duration = 0L
        var eventBytes = 0L
        events.need('{')
        if (!events.take('}')) {
            do {
                val key = events.string()
                events.need(':')
                when (key) {
                    "ts_ms" -> ts = events.long()
                    "route" -> route = events.string()
                    "status" -> status = events.long()
                    "duration_us" -> duration = events.long()
                    "bytes" -> eventBytes = events.long()
                    else -> events.skip()
                }
            } while (events.take(','))
            events.need('}')
        }
        if (ts >= start && ts < end) {
            val row = routes.getOrPut(normalize(route)) { Route() }
            count++
            bytes += eventBytes
            row.bytes += eventBytes
            if (status >= 500) { errors++; row.errors++ }
            row.add(duration)
        }
    } while (events.take(','))
    events.need(']')
    }
    val rows = JSONArray()
    for (name in routes.keys.sorted()) {
        val row = routes.getValue(name)
        val percentileIndex = ((95L * row.size + 99) / 100 - 1).toInt()
        rows.put(JSONObject().put("route", name).put("count", row.size.toLong())
            .put("errors", row.errors).put("total_bytes", row.bytes)
            .put("max_us", row.max)
            .put("p95_us", select(row.durations, row.size, percentileIndex)))
    }
    return JSONObject().put("routes", rows).put("total_count", count)
        .put("total_errors", errors).put("total_bytes", bytes)
}

// Median-of-three quickselect with a bounded sorting fallback for adversarial order.
private fun select(a: LongArray, size: Int, target: Int): Long {
    var lo = 0
    var hi = size - 1
    var budget = 2 * (32 - Integer.numberOfLeadingZeros(size))
    while (lo < hi) {
        if (hi - lo < 24 || budget-- == 0) {
            java.util.Arrays.sort(a, lo, hi + 1)
            return a[target]
        }
        val mid = (lo + hi) ushr 1
        val x = a[lo]; val y = a[mid]; val z = a[hi]
        val pivot = if (x < y) { if (y < z) y else maxOf(x, z) } else { if (x < z) x else maxOf(y, z) }
        var i = lo
        var j = hi
        while (i <= j) {
            while (a[i] < pivot) i++
            while (a[j] > pivot) j--
            if (i <= j) { val tmp = a[i]; a[i] = a[j]; a[j] = tmp; i++; j-- }
        }
        if (target <= j) hi = j else if (target >= i) lo = i else return a[target]
    }
    return a[target]
}

private fun telemetry(request: Request): JSONObject {
    val window = request.long("window")
    if (window <= 0) return error("invalid_window")
    val threshold = request.long("threshold")
    val samples = request.cursor("samples")
    val trailing = request.cursor("samples")
    samples.need('[')
    trailing.need('[')
    var n = 0L
    var sum = 0L
    var count = 0L
    var min = Long.MAX_VALUE
    var max = Long.MIN_VALUE
    var above = 0L
    var checksum = 0L
    if (!samples.take(']')) {
        do {
            val value = samples.long()
            if (n >= window) {
                sum -= trailing.long()
                trailing.take(',')
            }
            sum += value
            n++
            if (n >= window) {
                val average = sum / window
                count++
                min = minOf(min, average)
                max = maxOf(max, average)
                if (average > threshold) above++
                checksum += count * average
            }
        } while (samples.take(','))
        samples.need(']')
    }
    if (count == 0L) return error("invalid_window")
    return JSONObject().put("count", count).put("min", min).put("max", max)
        .put("above", above).put("weighted_checksum", checksum)
}

private class BadJson : RuntimeException(null, null, false, false)

// Validate without materializing a JSON object tree. Offsets permit arbitrary field order.
private class Cursor(val text: String, var pos: Int = 0) {
    fun fail(): Nothing = throw BadJson()
    fun ws() { while (pos < text.length && (text[pos] == ' ' || text[pos] == '\t' || text[pos] == '\r' || text[pos] == '\n')) pos++ }
    fun take(c: Char): Boolean { ws(); if (pos < text.length && text[pos] == c) { pos++; return true }; return false }
    fun need(c: Char) { if (!take(c)) fail() }
    fun string(decode: Boolean = true): String {
        need('"')
        val start = pos
        var builder: StringBuilder? = null
        var segment = pos
        while (pos < text.length) {
            val c = text[pos++]
            if (c == '"') {
                if (!decode) return ""
                if (builder == null) return text.substring(start, pos - 1)
                builder.append(text, segment, pos - 1)
                return builder.toString()
            }
            if (c < ' ') fail()
            if (c == '\\') {
                if (decode) {
                    if (builder == null) builder = StringBuilder()
                    builder.append(text, segment, pos - 1)
                }
                if (pos == text.length) fail()
                val escaped = when (val e = text[pos++]) {
                    '"', '\\', '/' -> e
                    'b' -> '\b'
                    'f' -> '\u000c'
                    'n' -> '\n'
                    'r' -> '\r'
                    't' -> '\t'
                    'u' -> {
                        if (text.length - pos < 4) fail()
                        var code = 0
                        repeat(4) {
                            val hex = text[pos++]
                            val digit = when (hex) {
                                in '0'..'9' -> hex - '0'
                                in 'a'..'f' -> hex - 'a' + 10
                                in 'A'..'F' -> hex - 'A' + 10
                                else -> fail()
                            }
                            code = code * 16 + digit
                        }
                        code.toChar()
                    }
                    else -> fail()
                }
                if (decode) builder!!.append(escaped)
                segment = pos
            }
        }
        fail()
    }
    fun numberEnd() {
        ws()
        if (pos < text.length && text[pos] == '-') pos++
        if (pos == text.length) fail()
        if (text[pos] == '0') pos++
        else {
            if (text[pos] !in '1'..'9') fail()
            while (pos < text.length && text[pos] in '0'..'9') pos++
        }
        if (pos < text.length && text[pos] == '.') {
            pos++
            val start = pos
            while (pos < text.length && text[pos] in '0'..'9') pos++
            if (pos == start) fail()
        }
        if (pos < text.length && (text[pos] == 'e' || text[pos] == 'E')) {
            pos++
            if (pos < text.length && (text[pos] == '+' || text[pos] == '-')) pos++
            val start = pos
            while (pos < text.length && text[pos] in '0'..'9') pos++
            if (pos == start) fail()
        }
    }
    fun long(): Long {
        ws()
        val start = pos
        var negative = false
        if (pos < text.length && text[pos] == '-') { negative = true; pos++ }
        val digits = pos
        var value = 0L
        while (pos < text.length && text[pos] in '0'..'9') value = value * 10 + (text[pos++] - '0')
        if (digits == pos) fail()
        if (pos < text.length && (text[pos] == '.' || text[pos] == 'e' || text[pos] == 'E')) {
            pos = start
            numberEnd()
            return java.math.BigDecimal(text.substring(start, pos)).longValueExact()
        }
        return if (negative) -value else value
    }
    fun skip() {
        var containers = CharArray(16)
        var depth = 0
        while (true) {
            ws()
            if (pos == text.length) fail()
            when (text[pos]) {
                '"' -> string(false)
                '{', '[' -> {
                    val kind = text[pos++]
                    val close = if (kind == '{') '}' else ']'
                    if (!take(close)) {
                        if (depth == containers.size) containers = containers.copyOf(depth * 2)
                        containers[depth++] = kind
                        if (kind == '{') { string(false); need(':') }
                        continue
                    }
                }
                't' -> literal("true")
                'f' -> literal("false")
                'n' -> literal("null")
                else -> numberEnd()
            }
            while (true) {
                if (depth == 0) return
                val kind = containers[depth - 1]
                if (take(if (kind == '{') '}' else ']')) { depth--; continue }
                need(',')
                if (kind == '{') { string(false); need(':') }
                break
            }
        }
    }
    private fun literal(s: String) { if (!text.startsWith(s, pos)) fail(); pos += s.length }
}

private class Request(val text: String) {
    val fields = HashMap<String, Int>()
    init {
        val c = Cursor(text)
        c.need('{')
        if (!c.take('}')) {
            do {
                val key = c.string()
                c.need(':'); c.ws()
                fields[key] = c.pos
                c.skip()
            } while (c.take(','))
            c.need('}')
        }
        c.ws()
        if (c.pos != text.length) c.fail()
    }
    fun cursor(key: String): Cursor = Cursor(text, fields[key] ?: throw BadJson())
    fun long(key: String): Long = cursor(key).long()
    fun op(): String {
        val c = fields["op"] ?: return ""
        return if (text[c] == '"') Cursor(text, c).string() else ""
    }
}

fun processLine(line: String): JSONObject {
    return try {
        val request = Request(line)
        when (request.op()) {
            "invoice" -> invoice(request)
            "access_log" -> accessLog(request)
            "telemetry" -> telemetry(request)
            else -> error("unknown_op")
        }
    } catch (_: BadJson) {
        error("invalid_json")
    } catch (_: ArithmeticException) {
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
