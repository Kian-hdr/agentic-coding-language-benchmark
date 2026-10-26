import Foundation

func isWhitespace(_ byte: UInt8) -> Bool {
    byte == 32 || (byte >= 9 && byte <= 13)
}

func normalizedAccount(_ text: String) -> String {
    let bytes = Array(text.utf8)
    var start = 0
    var end = bytes.count
    while start < end && isWhitespace(bytes[start]) { start += 1 }
    while end > start && isWhitespace(bytes[end - 1]) { end -= 1 }
    return String(decoding: bytes[start..<end], as: UTF8.self)
}

func ledger(_ request: [String: Any]) -> [String: Any] {
    var seen = Set<String>()
    var accounts: [String: (balance: Int, count: Int)] = [:]
    var accepted = 0
    for entry in request["entries"] as! [[String: Any]] {
        let id = entry["id"] as! String
        guard seen.insert(id).inserted else { continue }
        let account = normalizedAccount(entry["account"] as! String)
        if account.isEmpty { return ["error": "empty_account"] }
        let previous = accounts[account] ?? (balance: 0, count: 0)
        accounts[account] = (previous.balance + (entry["amount"] as! Int), previous.count + 1)
        accepted += 1
    }
    let rows: [[String: Any]] = accounts.keys.sorted {
        $0.utf8.lexicographicallyPrecedes($1.utf8)
    }.map { account in
        let totals = accounts[account]!
        return ["account": account, "balance": totals.balance, "count": totals.count]
    }
    return ["accounts": rows, "accepted": accepted]
}

struct MinHeap {
    var values: [Int] = []
    mutating func insert(_ value: Int) {
        values.append(value)
        var index = values.count - 1
        while index > 0 {
            let parent = (index - 1) / 2
            if values[parent] <= values[index] { break }
            values.swapAt(parent, index)
            index = parent
        }
    }
    mutating func pop() -> Int? {
        guard !values.isEmpty else { return nil }
        if values.count == 1 { return values.removeLast() }
        let result = values[0]
        values[0] = values.removeLast()
        var index = 0
        while index * 2 + 1 < values.count {
            var child = index * 2 + 1
            if child + 1 < values.count && values[child + 1] < values[child] { child += 1 }
            if values[index] <= values[child] { break }
            values.swapAt(index, child)
            index = child
        }
        return result
    }
}

func topo(_ request: [String: Any]) -> [String: Any] {
    let nodes = (request["nodes"] as! [String]).sorted {
        $0.utf8.lexicographicallyPrecedes($1.utf8)
    }
    let indices = Dictionary(uniqueKeysWithValues: nodes.enumerated().map { ($0.element, $0.offset) })
    var outgoing = Array(repeating: Set<Int>(), count: nodes.count)
    var indegrees = Array(repeating: 0, count: nodes.count)
    for edge in request["edges"] as! [[String]] {
        guard let source = indices[edge[0]], let target = indices[edge[1]] else {
            return ["error": "unknown_node"]
        }
        if outgoing[source].insert(target).inserted { indegrees[target] += 1 }
    }
    var available = MinHeap()
    for index in nodes.indices where indegrees[index] == 0 { available.insert(index) }
    var order: [String] = []
    while let source = available.pop() {
        order.append(nodes[source])
        for target in outgoing[source] {
            indegrees[target] -= 1
            if indegrees[target] == 0 { available.insert(target) }
        }
    }
    return order.count == nodes.count ? ["order": order] : ["error": "cycle"]
}

enum CalculationError: Error {
    case syntax
    case divisionByZero
}

struct Parser {
    let bytes: [UInt8]
    var index = 0

    mutating func skipWhitespace() {
        while index < bytes.count && isWhitespace(bytes[index]) { index += 1 }
    }

    mutating func evaluate() throws -> Int {
        let value = try expression()
        skipWhitespace()
        guard index == bytes.count else { throw CalculationError.syntax }
        return value
    }

    mutating func expression() throws -> Int {
        var value = try term()
        while true {
            skipWhitespace()
            guard index < bytes.count && (bytes[index] == 43 || bytes[index] == 45) else { return value }
            let op = bytes[index]
            index += 1
            let right = try term()
            value = op == 43 ? value + right : value - right
        }
    }

    mutating func term() throws -> Int {
        var value = try unary()
        while true {
            skipWhitespace()
            guard index < bytes.count && (bytes[index] == 42 || bytes[index] == 47) else { return value }
            let op = bytes[index]
            index += 1
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
        skipWhitespace()
        while index < bytes.count && (bytes[index] == 43 || bytes[index] == 45) {
            if bytes[index] == 45 { negative.toggle() }
            index += 1
            skipWhitespace()
        }
        let value = try primary()
        return negative ? -value : value
    }

    mutating func primary() throws -> Int {
        skipWhitespace()
        guard index < bytes.count else { throw CalculationError.syntax }
        if bytes[index] == 40 {
            index += 1
            let value = try expression()
            skipWhitespace()
            guard index < bytes.count && bytes[index] == 41 else { throw CalculationError.syntax }
            index += 1
            return value
        }
        guard bytes[index] >= 48 && bytes[index] <= 57 else { throw CalculationError.syntax }
        var value = 0
        while index < bytes.count && bytes[index] >= 48 && bytes[index] <= 57 {
            let (product, multiplicationOverflow) = value.multipliedReportingOverflow(by: 10)
            let (sum, additionOverflow) = product.addingReportingOverflow(Int(bytes[index] - 48))
            guard !multiplicationOverflow && !additionOverflow else { throw CalculationError.syntax }
            value = sum
            index += 1
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
        } catch CalculationError.divisionByZero {
            return ["error": "division_by_zero"]
        } catch {
            return ["error": "syntax"]
        }
    default: return ["error": "unknown_op"]
    }
}

let data = try Data(contentsOf: URL(fileURLWithPath: CommandLine.arguments[1]))
let request = try JSONSerialization.jsonObject(with: data) as! [String: Any]
let output = try JSONSerialization.data(withJSONObject: respond(request), options: [.sortedKeys])
FileHandle.standardOutput.write(output)
FileHandle.standardOutput.write(Data([10]))
