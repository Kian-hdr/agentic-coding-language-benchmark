import Foundation

func isWhitespace(_ byte: UInt8) -> Bool {
    byte == 32 || (byte >= 9 && byte <= 13)
}

func normalizedAccount(_ account: String) -> String {
    let bytes = Array(account.utf8)
    var start = 0
    var end = bytes.count
    while start < end && isWhitespace(bytes[start]) { start += 1 }
    while end > start && isWhitespace(bytes[end - 1]) { end -= 1 }
    return String(decoding: bytes[start..<end], as: UTF8.self)
}

func ledger(_ request: [String: Any]) -> [String: Any] {
    var seen = Set<String>()
    var accounts: [String: (balance: Int, count: Int)] = [:]
    for entry in request["entries"] as! [[String: Any]] {
        let id = entry["id"] as! String
        guard seen.insert(id).inserted else { continue }
        let account = normalizedAccount(entry["account"] as! String)
        if account.isEmpty { return ["error": "empty_account"] }
        let previous = accounts[account] ?? (balance: 0, count: 0)
        accounts[account] = (previous.balance + (entry["amount"] as! Int), previous.count + 1)
    }
    let rows: [[String: Any]] = accounts.keys.sorted().map { account in
        let totals = accounts[account]!
        return ["account": account, "balance": totals.balance, "count": totals.count]
    }
    return ["accounts": rows, "accepted": seen.count]
}

struct MinHeap {
    var values: [String] = []
    mutating func push(_ value: String) {
        values.append(value)
        var index = values.count - 1
        while index > 0 {
            let parent = (index - 1) / 2
            if values[parent] <= values[index] { break }
            values.swapAt(parent, index)
            index = parent
        }
    }
    mutating func pop() -> String? {
        guard !values.isEmpty else { return nil }
        if values.count == 1 { return values.removeLast() }
        let result = values[0]
        values[0] = values.removeLast()
        var index = 0
        while index * 2 + 1 < values.count {
            let left = index * 2 + 1
            let right = left + 1
            let child = right < values.count && values[right] < values[left] ? right : left
            if values[index] <= values[child] { break }
            values.swapAt(index, child)
            index = child
        }
        return result
    }
}

func topo(_ request: [String: Any]) -> [String: Any] {
    let nodes = request["nodes"] as! [String]
    let known = Set(nodes)
    var outgoing: [String: Set<String>] = [:]
    var indegree = Dictionary(uniqueKeysWithValues: nodes.map { ($0, 0) })
    for edge in request["edges"] as! [[String]] {
        let from = edge[0]
        let to = edge[1]
        guard known.contains(from), known.contains(to) else { return ["error": "unknown_node"] }
        if outgoing[from, default: []].insert(to).inserted {
            indegree[to]! += 1
        }
    }
    var available = MinHeap()
    for node in nodes where indegree[node] == 0 { available.push(node) }
    var order: [String] = []
    while let node = available.pop() {
        order.append(node)
        for next in outgoing[node] ?? [] {
            indegree[next]! -= 1
            if indegree[next] == 0 { available.push(next) }
        }
    }
    if order.count != nodes.count { return ["error": "cycle"] }
    return ["order": order]
}

enum CalculationError: String, Error {
    case syntax
    case divisionByZero = "division_by_zero"
}

struct Parser {
    let bytes: [UInt8]
    var position = 0

    mutating func skipWhitespace() {
        while position < bytes.count && isWhitespace(bytes[position]) { position += 1 }
    }

    mutating func evaluate() throws -> Int {
        let value = try expression()
        skipWhitespace()
        guard position == bytes.count else { throw CalculationError.syntax }
        return value
    }

    mutating func expression() throws -> Int {
        var value = try term()
        while true {
            skipWhitespace()
            guard position < bytes.count else { return value }
            let op = bytes[position]
            guard op == 43 || op == 45 else { return value }
            position += 1
            let right = try term()
            value = op == 43 ? value + right : value - right
        }
    }

    mutating func term() throws -> Int {
        var value = try unary()
        while true {
            skipWhitespace()
            guard position < bytes.count else { return value }
            let op = bytes[position]
            guard op == 42 || op == 47 else { return value }
            position += 1
            let right = try unary()
            if op == 47 {
                guard right != 0 else { throw CalculationError.divisionByZero }
                value /= right
            } else {
                value *= right
            }
        }
    }

    mutating func unary() throws -> Int {
        var negative = false
        while true {
            skipWhitespace()
            guard position < bytes.count else { throw CalculationError.syntax }
            if bytes[position] == 43 { position += 1 }
            else if bytes[position] == 45 { negative.toggle(); position += 1 }
            else { break }
        }
        let value = try primary()
        return negative ? -value : value
    }

    mutating func primary() throws -> Int {
        skipWhitespace()
        guard position < bytes.count else { throw CalculationError.syntax }
        if bytes[position] == 40 {
            position += 1
            let value = try expression()
            skipWhitespace()
            guard position < bytes.count && bytes[position] == 41 else { throw CalculationError.syntax }
            position += 1
            return value
        }
        guard bytes[position] >= 48 && bytes[position] <= 57 else { throw CalculationError.syntax }
        var value = 0
        while position < bytes.count && bytes[position] >= 48 && bytes[position] <= 57 {
            let (scaled, multiplyOverflow) = value.multipliedReportingOverflow(by: 10)
            let (next, addOverflow) = scaled.addingReportingOverflow(Int(bytes[position] - 48))
            guard !multiplyOverflow && !addOverflow else { throw CalculationError.syntax }
            value = next
            position += 1
        }
        return value
    }
}

func merge(_ request: [String: Any]) -> [String: Any] {
    let intervals = request["intervals"] as! [[Int]]
    guard intervals.allSatisfy({ $0[0] <= $0[1] }) else {
        return ["error": "invalid_interval"]
    }
    let sorted = intervals.sorted {
        $0[0] == $1[0] ? $0[1] < $1[1] : $0[0] < $1[0]
    }
    var merged: [[Int]] = []
    for interval in sorted {
        if let last = merged.last, interval[0] <= last[1] {
            merged[merged.count - 1][1] = max(last[1], interval[1])
        } else {
            merged.append(interval)
        }
    }
    return ["intervals": merged]
}

func respond(_ request: [String: Any]) -> [String: Any] {
    switch request["op"] as? String {
    case "ledger": return ledger(request)
    case "topo": return topo(request)
    case "merge": return merge(request)
    case "calc":
        do {
            var parser = Parser(bytes: Array((request["expr"] as! String).utf8))
            return ["value": try parser.evaluate()]
        } catch let error as CalculationError {
            return ["error": error.rawValue]
        } catch { return ["error": "syntax"] }
    default: return ["error": "unknown_op"]
    }
}

let data = try Data(contentsOf: URL(fileURLWithPath: CommandLine.arguments[1]))
let request = try JSONSerialization.jsonObject(with: data) as! [String: Any]
let output = try JSONSerialization.data(withJSONObject: respond(request), options: [.sortedKeys])
FileHandle.standardOutput.write(output)
FileHandle.standardOutput.write(Data([10]))
