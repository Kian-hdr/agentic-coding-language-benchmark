import java.io.File
import java.util.PriorityQueue
import org.json.JSONArray
import org.json.JSONObject

private fun asciiWhitespace(c: Char): Boolean = c == ' ' || c in '\t'..'\r'
private fun error(name: String): JSONObject = JSONObject().put("error", name)

fun process(request: JSONObject): JSONObject = when (request.getString("op")) {
    "ledger" -> ledger(request)
    "topo" -> topo(request)
    "calc" -> calculate(request.getString("expr"))
    "merge" -> merge(request)
    else -> error("unknown_op")
}

private fun merge(request: JSONObject): JSONObject {
    val input = request.getJSONArray("intervals")
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

private fun ledger(request: JSONObject): JSONObject {
    val seen = HashSet<String>()
    val accounts = sortedMapOf<String, Pair<Int, Int>>()
    val entries = request.getJSONArray("entries")
    for (i in 0 until entries.length()) {
        val entry = entries.getJSONObject(i)
        if (!seen.add(entry.getString("id"))) continue
        val account = entry.getString("account").trim(::asciiWhitespace)
        if (account.isEmpty()) return error("empty_account")
        val previous = accounts[account] ?: (0 to 0)
        accounts[account] = (previous.first + entry.getInt("amount")) to (previous.second + 1)
    }
    val result = JSONArray()
    for ((account, totals) in accounts) {
        result.put(JSONObject().put("account", account).put("balance", totals.first).put("count", totals.second))
    }
    return JSONObject().put("accounts", result).put("accepted", seen.size)
}

private fun topo(request: JSONObject): JSONObject {
    val nodes = request.getJSONArray("nodes")
    val outgoing = HashMap<String, MutableSet<String>>()
    val indegree = HashMap<String, Int>()
    for (i in 0 until nodes.length()) {
        val node = nodes.getString(i)
        outgoing[node] = HashSet()
        indegree[node] = 0
    }
    val edges = request.getJSONArray("edges")
    for (i in 0 until edges.length()) {
        val edge = edges.getJSONArray(i)
        val from = edge.getString(0)
        val to = edge.getString(1)
        val destinations = outgoing[from]
        if (destinations == null || !indegree.containsKey(to)) return error("unknown_node")
        if (destinations.add(to)) indegree[to] = indegree.getValue(to) + 1
    }
    val ready = PriorityQueue<String>()
    for ((node, degree) in indegree) if (degree == 0) ready.add(node)
    val order = JSONArray()
    while (ready.isNotEmpty()) {
        val node = ready.remove()
        order.put(node)
        for (next in outgoing.getValue(node)) {
            val degree = indegree.getValue(next) - 1
            indegree[next] = degree
            if (degree == 0) ready.add(next)
        }
    }
    return if (order.length() == nodes.length()) JSONObject().put("order", order) else error("cycle")
}

private class CalcFailure(val reason: String) : RuntimeException()

private fun calculate(expression: String): JSONObject {
    val values = ArrayList<Long>()
    val operators = ArrayList<Char>()
    fun precedence(op: Char): Int = when (op) {
        'p', 'n' -> 3
        '*', '/' -> 2
        '+', '-' -> 1
        else -> 0
    }
    fun applyOperator() {
        val op = operators.removeAt(operators.lastIndex)
        if (values.isEmpty()) throw CalcFailure("syntax")
        val right = values.removeAt(values.lastIndex)
        if (op == 'p' || op == 'n') {
            values.add(if (op == 'n') -right else right)
            return
        }
        if (values.isEmpty()) throw CalcFailure("syntax")
        val left = values.removeAt(values.lastIndex)
        values.add(when (op) {
            '+' -> left + right
            '-' -> left - right
            '*' -> left * right
            '/' -> {
                if (right == 0L) throw CalcFailure("division_by_zero")
                left / right
            }
            else -> throw CalcFailure("syntax")
        })
    }
    return try {
        var index = 0
        var expectOperand = true
        while (index < expression.length) {
            val c = expression[index]
            if (asciiWhitespace(c)) {
                index++
                continue
            }
            when {
                c in '0'..'9' -> {
                    if (!expectOperand) throw CalcFailure("syntax")
                    val start = index
                    while (index < expression.length && expression[index] in '0'..'9') index++
                    values.add(expression.substring(start, index).toLong())
                    expectOperand = false
                    continue
                }
                c == '(' -> {
                    if (!expectOperand) throw CalcFailure("syntax")
                    operators.add(c)
                }
                c == ')' -> {
                    if (expectOperand) throw CalcFailure("syntax")
                    while (operators.isNotEmpty() && operators.last() != '(') applyOperator()
                    if (operators.isEmpty()) throw CalcFailure("syntax")
                    operators.removeAt(operators.lastIndex)
                }
                c == '+' || c == '-' -> {
                    if (expectOperand) operators.add(if (c == '+') 'p' else 'n')
                    else {
                        while (operators.isNotEmpty() && precedence(operators.last()) >= precedence(c)) applyOperator()
                        operators.add(c)
                        expectOperand = true
                    }
                }
                c == '*' || c == '/' -> {
                    if (expectOperand) throw CalcFailure("syntax")
                    while (operators.isNotEmpty() && precedence(operators.last()) >= precedence(c)) applyOperator()
                    operators.add(c)
                    expectOperand = true
                }
                else -> throw CalcFailure("syntax")
            }
            index++
        }
        if (expectOperand) throw CalcFailure("syntax")
        while (operators.isNotEmpty()) {
            if (operators.last() == '(') throw CalcFailure("syntax")
            applyOperator()
        }
        if (values.size != 1) throw CalcFailure("syntax")
        JSONObject().put("value", values.single())
    } catch (failure: CalcFailure) {
        error(failure.reason)
    } catch (_: NumberFormatException) {
        error("syntax")
    }
}

fun main(args: Array<String>) {
    println(process(JSONObject(File(args[0]).readText())).toString())
}
