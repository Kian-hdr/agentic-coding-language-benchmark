import Foundation

enum RequestError: Error { case schema }

func integer(_ object: [String: Any], _ key: String) throws -> Int {
    guard let value = object[key] as? Int else { throw RequestError.schema }
    return value
}

func string(_ object: [String: Any], _ key: String) throws -> String {
    guard let value = object[key] as? String else { throw RequestError.schema }
    return value
}

let asciiWhitespace = CharacterSet(charactersIn: " \t\n\r\u{000B}\u{000C}")
func normalized(_ value: String) -> String {
    value.trimmingCharacters(in: asciiWhitespace)
}

struct Customer {
    var gross = 0
    var refund = 0
    var count = 0
    mutating func add(_ amount: Int, refund isRefund: Bool) {
        if isRefund { refund += amount } else { gross += amount }
        count += 1
    }
}

func invoice(_ request: [String: Any]) throws -> [String: Any] {
    guard let events = request["events"] as? [[String: Any]] else { throw RequestError.schema }
    var seen = Set<String>()
    seen.reserveCapacity(events.count)
    var customers: [String: Customer] = [:]
    var accepted = 0, duplicates = 0, ignored = 0, rejected = 0
    var gross = 0, refund = 0
    for event in events {
        let id = try string(event, "id")
        guard seen.insert(id).inserted else { duplicates += 1; continue }
        let customer = normalized(try string(event, "customer"))
        let amount = try integer(event, "amount_cents")
        let status = try string(event, "status")
        guard !customer.isEmpty, amount >= 0,
              status == "paid" || status == "refund" || status == "pending" || status == "void" else {
            rejected += 1
            continue
        }
        if status == "pending" || status == "void" { ignored += 1; continue }
        accepted += 1
        let isRefund = status == "refund"
        customers[customer, default: Customer()].add(amount, refund: isRefund)
        if isRefund { refund += amount } else { gross += amount }
    }
    let rows: [[String: Any]] = customers.keys.sorted().map { name in
        let value = customers[name]!
        return ["customer": name, "gross_cents": value.gross,
                "refund_cents": value.refund, "net_cents": value.gross - value.refund,
                "count": value.count]
    }
    return ["customers": rows, "accepted": accepted, "duplicates": duplicates,
            "ignored": ignored, "rejected": rejected, "gross_cents": gross,
            "refund_cents": refund, "net_cents": gross - refund]
}

struct Route {
    var count = 0
    var errors = 0
    var bytes = 0
    var max = 0
    var durations: [Int] = []
    mutating func add(duration: Int, bytes size: Int, error: Bool) {
        count += 1
        if error { errors += 1 }
        bytes += size
        if duration > max { max = duration }
        durations.append(duration)
    }
}

func accessLog(_ request: [String: Any]) throws -> [String: Any] {
    let start = try integer(request, "start_ms"), end = try integer(request, "end_ms")
    guard let events = request["events"] as? [[String: Any]] else { throw RequestError.schema }
    var routes: [String: Route] = [:]
    var count = 0, errors = 0, bytes = 0
    for event in events {
        let timestamp = try integer(event, "ts_ms")
        guard timestamp >= start && timestamp < end else { continue }
        let route = normalized(try string(event, "route"))
        let duration = try integer(event, "duration_us")
        let size = try integer(event, "bytes")
        let isError = try integer(event, "status") >= 500
        routes[route, default: Route()].add(duration: duration, bytes: size, error: isError)
        count += 1
        if isError { errors += 1 }
        bytes += size
    }
    let rows: [[String: Any]] = routes.keys.sorted().map { name in
        let route = routes[name]!
        let sorted = route.durations.sorted()
        let index = (95 * route.count + 99) / 100 - 1
        return ["route": name, "count": route.count, "errors": route.errors,
                "total_bytes": route.bytes, "max_us": route.max, "p95_us": sorted[index]]
    }
    return ["routes": rows, "total_count": count, "total_errors": errors, "total_bytes": bytes]
}

func telemetry(_ request: [String: Any]) throws -> [String: Any] {
    guard let samples = request["samples"] as? [Int] else { throw RequestError.schema }
    let window = try integer(request, "window")
    let threshold = try integer(request, "threshold")
    guard window > 0 && window <= samples.count else { return ["error": "invalid_window"] }
    var sum = 0
    for i in 0..<window { sum += samples[i] }
    let count = samples.count - window + 1
    var minimum = Int.max, maximum = Int.min, above = 0, checksum = 0
    for i in 0..<count {
        if i > 0 {
            sum -= samples[i - 1]
            sum += samples[i + window - 1]
        }
        let average = sum / window
        if average < minimum { minimum = average }
        if average > maximum { maximum = average }
        if average > threshold { above += 1 }
        checksum += (i + 1) * average
    }
    return ["count": count, "min": minimum, "max": maximum,
            "above": above, "weighted_checksum": checksum]
}

func response(_ line: Data) -> [String: Any] {
    do {
        let value = try JSONSerialization.jsonObject(with: line, options: [.fragmentsAllowed])
        guard let request = value as? [String: Any], let op = request["op"] as? String else {
            return ["error": "unknown_op"]
        }
        switch op {
        case "invoice": return try invoice(request)
        case "access_log": return try accessLog(request)
        case "telemetry": return try telemetry(request)
        default: return ["error": "unknown_op"]
        }
    } catch {
        return ["error": "invalid_json"]
    }
}

func isWhitespace(_ byte: UInt8) -> Bool {
    byte == 32 || (byte >= 9 && byte <= 13)
}

func run(inputPath: String, outputPath: String) throws {
    // Open input before creating output so missing inputs cannot truncate output.
    let input = try FileHandle(forReadingFrom: URL(fileURLWithPath: inputPath))
    defer { try? input.close() }
    guard FileManager.default.createFile(atPath: outputPath, contents: nil) else {
        throw NSError(domain: "Worker", code: 1,
                      userInfo: [NSLocalizedDescriptionKey: "Cannot create output file"])
    }
    let output = try FileHandle(forWritingTo: URL(fileURLWithPath: outputPath))
    defer { try? output.close() }
    try output.truncate(atOffset: 0)
    var pending = Data()
    var bufferedOutput = Data()
    func emit(_ line: Data) throws {
        if line.allSatisfy(isWhitespace) { return }
        let result = response(line)
        bufferedOutput.append(try JSONSerialization.data(withJSONObject: result, options: [.sortedKeys]))
        bufferedOutput.append(10)
        if bufferedOutput.count >= 65536 {
            try output.write(contentsOf: bufferedOutput)
            bufferedOutput.removeAll(keepingCapacity: true)
        }
    }
    while let chunk = try input.read(upToCount: 65536), !chunk.isEmpty {
        pending.append(chunk)
        var beginning = pending.startIndex
        for index in pending.indices where pending[index] == 10 {
            try emit(pending.subdata(in: beginning..<index))
            beginning = index + 1
        }
        if beginning > pending.startIndex { pending.removeSubrange(pending.startIndex..<beginning) }
    }
    if !pending.isEmpty { try emit(pending) }
    if !bufferedOutput.isEmpty { try output.write(contentsOf: bufferedOutput) }
}

guard CommandLine.arguments.count == 3 else {
    FileHandle.standardError.write(Data("Usage: worker.sh INPUT_JSONL OUTPUT_JSONL\n".utf8))
    exit(2)
}
do {
    try run(inputPath: CommandLine.arguments[1], outputPath: CommandLine.arguments[2])
} catch {
    FileHandle.standardError.write(Data("Worker: \(error.localizedDescription)\n".utf8))
    exit(1)
}
