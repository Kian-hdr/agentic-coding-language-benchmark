import Foundation

enum RequestError: Error { case schema }

// A typed JSON reader avoids Foundation's boxed numbers and per-event dictionaries.
struct Event {
    var id = "", name = "", status = ""
    var amount = 0, timestamp = 0, code = 0, duration = 0, bytes = 0
}
struct Request {
    var op = "", events: [Event] = [], samples: [Int] = []
    var start = 0, end = 0, window = 0, threshold = 0
}
struct Parser {
    let b: UnsafeBufferPointer<UInt8>
    var i = 0
    mutating func ws() { while i < b.count && (b[i] == 32 || b[i] == 9 || b[i] == 10 || b[i] == 13) { i += 1 } }
    mutating func take(_ c: UInt8) throws { ws(); guard i < b.count && b[i] == c else { throw RequestError.schema }; i += 1 }
    mutating func end(_ c: UInt8) -> Bool { ws(); if i < b.count && b[i] == c { i += 1; return true }; return false }
    mutating func hex() throws -> UInt32 {
        var n: UInt32 = 0
        for _ in 0..<4 {
            guard i < b.count else { throw RequestError.schema }
            let c = b[i]; i += 1
            let v: UInt8
            switch c { case 48...57: v = c - 48; case 65...70: v = c - 55; case 97...102: v = c - 87; default: throw RequestError.schema }
            n = n * 16 + UInt32(v)
        }
        return n
    }
    mutating func str() throws -> String {
        try take(34)
        let start = i
        while i < b.count && b[i] != 34 && b[i] != 92 {
            guard b[i] >= 32 else { throw RequestError.schema }; i += 1
        }
        guard i < b.count else { throw RequestError.schema }
        if b[i] == 34 {
            guard let s = String(bytes: b[start..<i], encoding: .utf8) else { throw RequestError.schema }
            i += 1; return s
        }
        var out = Array(b[start..<i])
        while i < b.count {
            let c = b[i]; i += 1
            if c == 34 {
                guard let s = String(bytes: out, encoding: .utf8) else { throw RequestError.schema }; return s
            }
            guard c >= 32 else { throw RequestError.schema }
            if c != 92 { out.append(c); continue }
            guard i < b.count else { throw RequestError.schema }
            let e = b[i]; i += 1
            switch e {
            case 34, 92, 47: out.append(e)
            case 98: out.append(8)
            case 102: out.append(12)
            case 110: out.append(10)
            case 114: out.append(13)
            case 116: out.append(9)
            case 117:
                var u = try hex()
                if u >= 0xD800 && u <= 0xDBFF {
                    guard i + 1 < b.count && b[i] == 92 && b[i+1] == 117 else { throw RequestError.schema }
                    i += 2; let low = try hex()
                    guard low >= 0xDC00 && low <= 0xDFFF else { throw RequestError.schema }
                    u = 0x10000 + (u - 0xD800) * 1024 + low - 0xDC00
                }
                guard let scalar = UnicodeScalar(u) else { throw RequestError.schema }
                out.append(contentsOf: String(scalar).utf8)
            default: throw RequestError.schema
            }
        }
        throw RequestError.schema
    }
    mutating func number() throws -> Range<Int> {
        ws(); let start = i
        if i < b.count && b[i] == 45 { i += 1 }
        guard i < b.count else { throw RequestError.schema }
        if b[i] == 48 { i += 1 } else {
            guard b[i] >= 49 && b[i] <= 57 else { throw RequestError.schema }
            repeat { i += 1 } while i < b.count && b[i] >= 48 && b[i] <= 57
        }
        if i < b.count && b[i] == 46 {
            i += 1; let first = i
            while i < b.count && b[i] >= 48 && b[i] <= 57 { i += 1 }
            guard i > first else { throw RequestError.schema }
        }
        if i < b.count && (b[i] == 101 || b[i] == 69) {
            i += 1
            if i < b.count && (b[i] == 43 || b[i] == 45) { i += 1 }
            let first = i
            while i < b.count && b[i] >= 48 && b[i] <= 57 { i += 1 }
            guard i > first else { throw RequestError.schema }
        }
        return start..<i
    }
    mutating func int() throws -> Int {
        let r = try number()
        var p = r.lowerBound, value = 0
        let negative = b[p] == 45
        if negative { p += 1 }
        while p < r.upperBound {
            let c = b[p]
            if c < 48 || c > 57 {
                let s = String(decoding: b[r], as: UTF8.self)
                guard let d = Double(s), let n = Int(exactly: d) else { throw RequestError.schema }; return n
            }
            let (v, overflow) = value.multipliedReportingOverflow(by: 10)
            let (n, overflow2) = v.addingReportingOverflow(Int(c - 48))
            guard !overflow && !overflow2 else { throw RequestError.schema }
            value = n; p += 1
        }
        return negative ? -value : value
    }
    mutating func skip() throws {
        // Explicit grammar stack handles nested ignored values without recursion.
        var stack: [UInt8] = [0]
        while let state = stack.last {
            ws(); guard i < b.count else { throw RequestError.schema }
            switch state {
            case 0:
                stack.removeLast()
                switch b[i] {
                case 34: _ = try str()
                case 123: i += 1; stack.append(1)
                case 91: i += 1; stack.append(3)
                case 116, 102, 110:
                    let literal: [UInt8] = b[i] == 116 ? [116,114,117,101] : b[i] == 102 ? [102,97,108,115,101] : [110,117,108,108]
                    for c in literal { guard i < b.count && b[i] == c else { throw RequestError.schema }; i += 1 }
                default: _ = try number()
                }
            case 1:
                if end(125) { stack.removeLast() }
                else { _ = try str(); try take(58); stack[stack.count-1] = 2; stack.append(0) }
            case 2:
                if end(125) { stack.removeLast() }
                else { try take(44); _ = try str(); try take(58); stack.append(0) }
            case 3:
                if end(93) { stack.removeLast() }
                else { stack[stack.count-1] = 4; stack.append(0) }
            default:
                if end(93) { stack.removeLast() }
                else { try take(44); stack.append(0) }
            }
        }
    }
    mutating func genericOp() throws -> String {
        var op = ""
        ws()
        if i < b.count && b[i] == 123 {
            i += 1
            if !end(125) {
                repeat {
                    let key = try str(); try take(58); ws()
                    if key == "op" && i < b.count && b[i] == 34 { op = try str() }
                    else { try skip(); if key == "op" { op = "" } }
                    if end(125) { break }; try take(44)
                } while true
            }
        } else { try skip() }
        ws(); guard i == b.count else { throw RequestError.schema }
        return op
    }
    mutating func event() throws -> Event {
        var e = Event(); try take(123)
        if end(125) { return e }
        repeat {
            let k = try str(); try take(58)
            switch k {
            case "id": e.id = try str()
            case "customer", "route": e.name = try str()
            case "status":
                ws(); if i < b.count && b[i] == 34 { e.status = try str() } else { e.code = try int() }
            case "amount_cents": e.amount = try int()
            case "ts_ms": e.timestamp = try int()
            case "duration_us": e.duration = try int()
            case "bytes": e.bytes = try int()
            default: try skip()
            }
            if end(125) { return e }; try take(44)
        } while true
    }
    mutating func request() throws -> Request {
        ws()
        guard i < b.count && b[i] == 123 else { try skip(); ws(); guard i == b.count else { throw RequestError.schema }; return Request() }
        var r = Request(); try take(123)
        if !end(125) {
            repeat {
                let k = try str(); try take(58)
                switch k {
                case "op":
                    ws(); if i < b.count && b[i] == 34 { r.op = try str() } else { try skip(); r.op = "" }
                case "start_ms": r.start = try int()
                case "end_ms": r.end = try int()
                case "window": r.window = try int()
                case "threshold": r.threshold = try int()
                case "events":
                    r.events.removeAll(keepingCapacity: true); try take(91)
                    if !end(93) { repeat { r.events.append(try event()); if end(93) { break }; try take(44) } while true }
                case "samples":
                    r.samples.removeAll(keepingCapacity: true); try take(91)
                    if !end(93) { repeat { r.samples.append(try int()); if end(93) { break }; try take(44) } while true }
                default: try skip()
                }
                if end(125) { break }; try take(44)
            } while true
        }
        ws(); guard i == b.count else { throw RequestError.schema }; return r
    }
}


func normalized(_ value: String) -> String {
    let bytes = value.utf8
    var first = bytes.startIndex, last = bytes.endIndex
    while first < last && isWhitespace(bytes[first]) { first = bytes.index(after: first) }
    while first < last && isWhitespace(bytes[bytes.index(before: last)]) { last = bytes.index(before: last) }
    if first == bytes.startIndex && last == bytes.endIndex { return value }
    return String(decoding: bytes[first..<last], as: UTF8.self)
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

func invoice(_ request: Request) throws -> [String: Any] {
    let events = request.events
    var seen = Set<String>()
    seen.reserveCapacity(events.count)
    var customers: [String: Customer] = [:]
    var accepted = 0, duplicates = 0, ignored = 0, rejected = 0
    var gross = 0, refund = 0
    for event in events {
        let id = event.id
        guard seen.insert(id).inserted else { duplicates += 1; continue }
        let customer = normalized(event.name)
        let amount = event.amount
        let status = event.status
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

// Three-way selection keeps repeated durations linear; the work budget bounds
// adversarial partitions by falling back to the standard library sort.
func percentile(_ values: inout [Int], _ target: Int) -> Int {
    var lo = 0, hi = values.count, budget = values.count * 4
    while hi - lo > 24 {
        if budget <= 0 { values[lo..<hi].sort(); return values[target] }
        budget -= hi - lo
        let a = values[lo], b = values[(lo + hi) / 2], c = values[hi - 1]
        let pivot = max(min(a, b), min(max(a, b), c))
        var lower = lo, cursor = lo, upper = hi
        while cursor < upper {
            if values[cursor] < pivot {
                values.swapAt(lower, cursor); lower += 1; cursor += 1
            } else if values[cursor] > pivot {
                upper -= 1; values.swapAt(cursor, upper)
            } else { cursor += 1 }
        }
        if target < lower { hi = lower }
        else if target >= upper { lo = upper }
        else { return pivot }
    }
    values[lo..<hi].sort()
    return values[target]
}

func accessLog(_ request: Request) throws -> [String: Any] {
    let start = request.start, end = request.end
    let events = request.events
    var routes: [String: Route] = [:]
    var count = 0, errors = 0, bytes = 0
    for event in events {
        let timestamp = event.timestamp
        guard timestamp >= start && timestamp < end else { continue }
        let route = normalized(event.name)
        let duration = event.duration
        let size = event.bytes
        let isError = event.code >= 500
        routes[route, default: Route()].add(duration: duration, bytes: size, error: isError)
        count += 1
        if isError { errors += 1 }
        bytes += size
    }
    let rows: [[String: Any]] = routes.keys.sorted().map { name in
        var route = routes.removeValue(forKey: name)!
        let index = route.count - route.count / 20 - 1
        let p95 = percentile(&route.durations, index)
        return ["route": name, "count": route.count, "errors": route.errors,
                "total_bytes": route.bytes, "max_us": route.max, "p95_us": p95]
    }
    return ["routes": rows, "total_count": count, "total_errors": errors, "total_bytes": bytes]
}

func telemetry(_ request: Request) throws -> [String: Any] {
    let samples = request.samples
    let window = request.window
    let threshold = request.threshold
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
        let request = try line.withUnsafeBytes { raw -> Request in
            var parser = Parser(b: raw.bindMemory(to: UInt8.self))
            return try parser.request()
        }
        switch request.op {
        case "invoice": return try invoice(request)
        case "access_log": return try accessLog(request)
        case "telemetry": return try telemetry(request)
        default: return ["error": "unknown_op"]
        }
    } catch {
        if let op = try? line.withUnsafeBytes({ raw -> String in
            var parser = Parser(b: raw.bindMemory(to: UInt8.self))
            return try parser.genericOp()
        }), op != "invoice" && op != "access_log" && op != "telemetry" {
            return ["error": "unknown_op"]
        }
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
    while try autoreleasepool(invoking: { () throws -> Bool in
        guard let chunk = try input.read(upToCount: 65536), !chunk.isEmpty else { return false }
        // Scan each incoming byte once, even when a request spans many chunks.
        var beginning = chunk.startIndex
        for index in chunk.indices where chunk[index] == 10 {
            if pending.isEmpty {
                try emit(chunk.subdata(in: beginning..<index))
            } else {
                pending.append(chunk[beginning..<index])
                try emit(pending)
                pending.removeAll(keepingCapacity: true)
            }
            beginning = index + 1
        }
        if beginning < chunk.endIndex { pending.append(chunk[beginning..<chunk.endIndex]) }
        return true
    }) {}
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
