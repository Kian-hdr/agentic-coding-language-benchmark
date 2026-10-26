import java.io.File
import java.math.BigInteger
import java.util.PriorityQueue
import org.json.JSONArray
import org.json.JSONObject

private fun asciiWhitespace(c: Char): Boolean = c == ' ' || c in '\t'..'\r'
private fun error(name: String) = JSONObject().put("error", name)

fun process(req: JSONObject): JSONObject = when (req.getString("op")) {
    "ledger" -> ledger(req)
    "topo" -> topo(req)
    "merge" -> merge(req)
    "calc" -> try {
        JSONObject().put("value", Calculator(req.getString("expr")).evaluate())
    } catch (_: SyntaxError) {
        error("syntax")
    } catch (_: ZeroDivision) {
        error("division_by_zero")
    }
    else -> error("unknown_op")
}

private fun merge(req: JSONObject): JSONObject {
    val input = req.getJSONArray("intervals")
    val intervals = ArrayList<Pair<Int, Int>>(input.length())
    for (i in 0 until input.length()) {
        val interval = input.getJSONArray(i)
        val start = interval.getInt(0)
        val end = interval.getInt(1)
        if (start > end) return error("invalid_interval")
        intervals.add(start to end)
    }
    intervals.sortWith(compareBy<Pair<Int, Int>> { it.first }.thenBy { it.second })
    val result = JSONArray()
    if (intervals.isNotEmpty()) {
        var start = intervals[0].first
        var end = intervals[0].second
        for (i in 1 until intervals.size) {
            val next = intervals[i]
            if (next.first <= end) {
                end = maxOf(end, next.second)
            } else {
                result.put(JSONArray().put(start).put(end))
                start = next.first
                end = next.second
            }
        }
        result.put(JSONArray().put(start).put(end))
    }
    return JSONObject().put("intervals", result)
}

private data class Account(var balance: Int = 0, var count: Int = 0)
private fun ledger(req: JSONObject): JSONObject {
    val seen = HashSet<String>()
    val accounts = sortedMapOf<String, Account>()
    val entries = req.getJSONArray("entries")
    var accepted = 0
    for (i in 0 until entries.length()) {
        val entry = entries.getJSONObject(i)
        if (!seen.add(entry.getString("id"))) continue
        val name = entry.getString("account").trim(::asciiWhitespace)
        if (name.isEmpty()) return error("empty_account")
        val account = accounts.getOrPut(name) { Account() }
        account.balance += entry.getInt("amount")
        account.count++
        accepted++
    }
    val result = JSONArray()
    for ((name, account) in accounts) {
        result.put(JSONObject().put("account", name).put("balance", account.balance).put("count", account.count))
    }
    return JSONObject().put("accounts", result).put("accepted", accepted)
}

private fun topo(req: JSONObject): JSONObject {
    val nodes = req.getJSONArray("nodes")
    val outgoing = HashMap<String, MutableSet<String>>()
    val indegree = HashMap<String, Int>()
    for (i in 0 until nodes.length()) {
        val node = nodes.getString(i)
        outgoing[node] = HashSet()
        indegree[node] = 0
    }
    val edges = req.getJSONArray("edges")
    for (i in 0 until edges.length()) {
        val edge = edges.getJSONArray(i)
        val from = edge.getString(0)
        val to = edge.getString(1)
        val targets = outgoing[from]
        if (targets == null || !indegree.containsKey(to)) return error("unknown_node")
        if (targets.add(to)) indegree[to] = indegree.getValue(to) + 1
    }
    val ready = PriorityQueue<String>()
    for ((node, degree) in indegree) if (degree == 0) ready.add(node)
    val order = JSONArray()
    while (ready.isNotEmpty()) {
        val node = ready.remove()
        order.put(node)
        for (target in outgoing.getValue(node)) {
            val degree = indegree.getValue(target) - 1
            indegree[target] = degree
            if (degree == 0) ready.add(target)
        }
    }
    return if (order.length() == nodes.length()) JSONObject().put("order", order) else error("cycle")
}

private class SyntaxError : RuntimeException()
private class ZeroDivision : RuntimeException()
private class Calculator(private val source: String) {
    private var position = 0
    private fun skip() {
        while (position < source.length && asciiWhitespace(source[position])) position++
    }
    private fun take(c: Char): Boolean {
        skip()
        if (position < source.length && source[position] == c) {
            position++
            return true
        }
        return false
    }
    fun evaluate(): BigInteger {
        val result = expression()
        skip()
        if (position != source.length) throw SyntaxError()
        return result
    }
    private fun expression(): BigInteger {
        var value = product()
        while (true) {
            value = when {
                take('+') -> value + product()
                take('-') -> value - product()
                else -> return value
            }
        }
    }
    private fun product(): BigInteger {
        var value = unary()
        while (true) {
            value = when {
                take('*') -> value * unary()
                take('/') -> {
                    val divisor = unary()
                    if (divisor == BigInteger.ZERO) throw ZeroDivision()
                    value / divisor
                }
                else -> return value
            }
        }
    }
    private fun unary(): BigInteger {
        var negative = false
        while (true) {
            when {
                take('+') -> Unit
                take('-') -> negative = !negative
                else -> break
            }
        }
        val value = atom()
        return if (negative) -value else value
    }
    private fun atom(): BigInteger {
        if (take('(')) {
            val value = expression()
            if (!take(')')) throw SyntaxError()
            return value
        }
        skip()
        val start = position
        while (position < source.length && source[position] in '0'..'9') position++
        if (position == start) throw SyntaxError()
        return source.substring(start, position).toBigInteger()
    }
}

fun main(args: Array<String>) {
    val req = JSONObject(File(args[0]).readText())
    println(process(req).toString())
}
