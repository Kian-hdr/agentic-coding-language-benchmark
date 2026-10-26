import Foundation

let root = URL(fileURLWithPath: FileManager.default.currentDirectoryPath)
let directory = root.appendingPathComponent(".test_artifacts", isDirectory: true)
try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
var input = Data()
var expected: [[String: Any]] = []
func add(_ request: [String: Any], _ result: [String: Any]) throws {
    input.append(try JSONSerialization.data(withJSONObject: request, options: [.sortedKeys]))
    input.append(contentsOf: expected.count % 2 == 0 ? [13, 10] : [10])
    expected.append(result)
}
func raw(_ text: String, _ result: [String: Any]) {
    input.append(Data((text + "\n").utf8)); expected.append(result)
}
func check(_ condition: Bool, _ message: String) {
    if !condition { fatalError(message) }
}
let invalid = ["error": "invalid_json"]
let unknown = ["error": "unknown_op"]
raw("{", invalid)
raw("{\"op\":\"invoice\",}", invalid)
raw("{\"op\":\"unknown\"}", unknown)
raw("[]", unknown)
input.append(Data("\n \t\r\n".utf8))
try add(["op":"invoice", "events":[]], ["customers":[], "accepted":0, "duplicates":0, "ignored":0, "rejected":0, "gross_cents":0, "refund_cents":0, "net_cents":0])
let invoiceRequest: [String: Any] = ["op":"invoice", "events":[
    ["id":"bad", "customer":" ", "amount_cents":1, "status":"paid"],
    ["id":"bad", "customer":"A", "amount_cents":99, "status":"paid"],
    ["id":"p", "customer":"\tA\u{000B}\u{000C}", "amount_cents":4_294_967_299, "status":"paid"],
    ["id":"r", "customer":"A", "amount_cents":4_294_967_299, "status":"refund"],
    ["id":"i", "customer":"B", "amount_cents":0, "status":"pending"],
    ["id":"i2", "customer":"B", "amount_cents":-1, "status":"void"],
    ["id":"i3", "customer":"B", "amount_cents":2, "status":"bad"],
    ["id":"z", "customer":"a", "amount_cents":0, "status":"refund"],
    ["id":"a", "customer":"AA", "amount_cents":3, "status":"paid"]]]
let invoiceResult: [String: Any] = ["customers":[
    ["customer":"A", "gross_cents":4_294_967_299, "refund_cents":4_294_967_299, "net_cents":0, "count":2],
    ["customer":"AA", "gross_cents":3, "refund_cents":0, "net_cents":3, "count":1],
    ["customer":"a", "gross_cents":0, "refund_cents":0, "net_cents":0, "count":1]],
    "accepted":4, "duplicates":1, "ignored":1, "rejected":3,
    "gross_cents":4_294_967_302, "refund_cents":4_294_967_299, "net_cents":3]
try add(invoiceRequest, invoiceResult)
try add(["op":"telemetry", "samples":[-2,5,8,1], "window":2, "threshold":3], ["count":3, "min":1, "max":6, "above":2, "weighted_checksum":25])
try add(invoiceRequest, invoiceResult)
for w in [-1,0,1,3] {
    try add(["op":"telemetry", "samples":[], "window":w, "threshold":0], ["error":"invalid_window"])
}
let limit = 9_007_199_254_740_991
try add(["op":"telemetry", "samples":[limit], "window":1, "threshold":limit], ["count":1, "min":limit, "max":limit, "above":0, "weighted_checksum":limit])
try add(["op":"telemetry", "samples":[-limit], "window":1, "threshold":0], ["count":1, "min":-limit, "max":-limit, "above":0, "weighted_checksum":-limit])
try add(["op":"access_log", "start_ms":10, "end_ms":10, "events":[]], ["routes":[], "total_count":0, "total_errors":0, "total_bytes":0])
var seed: UInt64 = 1234567
func random(_ upper: Int) -> Int {
    seed = seed &* 6364136223846793005 &+ 1442695040888963407
    return Int((seed >> 32) % UInt64(upper))
}
for _ in 0..<250 {
    let count = 1 + random(200)
    let samples = (0..<count).map { _ in random(2_000_001) - 1_000_000 }
    let window = 1 + random(count)
    let threshold = random(200001) - 100000
    let averages = (0...(count-window)).map { offset in samples[offset..<(offset+window)].reduce(0,+) / window }
    let checksum = averages.enumerated().reduce(0) { $0 + ($1.offset + 1) * $1.element }
    try add(["op":"telemetry", "samples":samples, "window":window, "threshold":threshold], ["count":averages.count, "min":averages.min()!, "max":averages.max()!, "above":averages.filter{$0 > threshold}.count, "weighted_checksum":checksum])
}
let trim = CharacterSet(charactersIn:" \t\r\n\u{000B}\u{000C}")
for _ in 0..<100 {
    let events: [[String: Any]] = (0..<random(150)).map { _ in
        ["ts_ms": random(40)-10, "route": [" /z "," /a ","\t/aa\r", "  "][random(4)], "status": [200,499,500,503][random(4)], "duration_us": random(1000000), "bytes": 4_294_967_296 + random(100)]
    }
    let included = events.filter { ($0["ts_ms"] as! Int) >= 0 && ($0["ts_ms"] as! Int) < 20 }
    let names = Set(included.map { ($0["route"] as! String).trimmingCharacters(in:trim) }).sorted()
    let rows: [[String: Any]] = names.map { name in
        let group = included.filter { ($0["route"] as! String).trimmingCharacters(in:trim) == name }
        let durations = group.map { $0["duration_us"] as! Int }.sorted()
        return ["route":name,"count":group.count,"errors":group.filter{($0["status"] as! Int) >= 500}.count,"total_bytes":group.reduce(0){$0 + ($1["bytes"] as! Int)},"max_us":durations.last!,"p95_us":durations[Int(ceil(Double(group.count)*0.95))-1]]
    }
    try add(["op":"access_log","start_ms":0,"end_ms":20,"events":events], ["routes":rows,"total_count":included.count,"total_errors":included.filter{($0["status"] as! Int)>=500}.count,"total_bytes":included.reduce(0){$0+($1["bytes"] as! Int)}])
}
for _ in 0..<100 {
    let events: [[String: Any]] = (0..<random(150)).map { _ in
        ["id":"e\(random(60))", "customer":[" A ","AA","\ta\u{000B}"," "][random(4)], "amount_cents":random(100)-5,"status":["paid","refund","pending","void","bad"][random(5)]]
    }
    var seen = Set<String>(), accepted: [[String: Any]] = []
    var duplicates = 0, rejected = 0, ignored = 0
    for var e in events {
        if seen.contains(e["id"] as! String) { duplicates += 1; continue }
        seen.insert(e["id"] as! String)
        let name = (e["customer"] as! String).trimmingCharacters(in:trim)
        let status = e["status"] as! String
        if name.isEmpty || (e["amount_cents"] as! Int) < 0 || !["paid","refund","pending","void"].contains(status) { rejected += 1; continue }
        if ["pending","void"].contains(status) { ignored += 1; continue }
        e["customer"] = name; accepted.append(e)
    }
    let names = Set(accepted.map{$0["customer"] as! String}).sorted()
    func total(_ entries: [[String: Any]], _ status: String) -> Int { entries.filter{($0["status"] as! String)==status}.reduce(0){$0+($1["amount_cents"] as! Int)} }
    let rows: [[String: Any]] = names.map { name in
        let group = accepted.filter{($0["customer"] as! String)==name}
        let gross = total(group,"paid"), refund = total(group,"refund")
        return ["customer":name,"count":group.count,"gross_cents":gross,"refund_cents":refund,"net_cents":gross-refund]
    }
    let gross = total(accepted,"paid"), refund = total(accepted,"refund")
    try add(["op":"invoice","events":events], ["customers":rows,"accepted":accepted.count,"duplicates":duplicates,"ignored":ignored,"rejected":rejected,"gross_cents":gross,"refund_cents":refund,"net_cents":gross-refund])
    for bps in [0, random(1001), 1000] {
        func fees(_ entries: [[String: Any]]) -> Int {
            entries.filter { ($0["status"] as! String) == "paid" }.reduce(0) {
                let product = ($1["amount_cents"] as! Int) * bps
                return $0 + product / 10000 + (product % 10000 >= 5000 ? 1 : 0)
            }
        }
        let feeRows: [[String: Any]] = rows.map { row in
            var result = row
            let fee = fees(accepted.filter { ($0["customer"] as! String) == (row["customer"] as! String) })
            result["fee_cents"] = fee
            result["net_cents"] = (row["net_cents"] as! Int) - fee
            return result
        }
        let fee = fees(accepted)
        try add(["op":"invoice","events":events,"fee_bps":bps], ["customers":feeRows,"accepted":accepted.count,"duplicates":duplicates,"ignored":ignored,"rejected":rejected,"gross_cents":gross,"refund_cents":refund,"fee_cents":fee,"net_cents":gross-refund-fee])
    }
}
// Fees round each accepted paid event independently, before aggregation.
for bps in [0, 1, 250, 1000] {
    let amounts = [0, 4, 5, 6, 49, 50, 51, 4_294_967_299, 9_007_199_249_735]
    var events: [[String: Any]] = amounts.enumerated().map {
        ["id":"f\($0.offset)", "customer":" A ", "amount_cents":$0.element, "status":"paid"]
    }
    events += [
        ["id":"f2", "customer":"A", "amount_cents":900, "status":"paid"],
        ["id":"refund", "customer":"A", "amount_cents":999, "status":"refund"],
        ["id":"only_refund", "customer":"B", "amount_cents":5, "status":"refund"],
        ["id":"pending", "customer":"C", "amount_cents":999, "status":"pending"],
        ["id":"void", "customer":"C", "amount_cents":999, "status":"void"],
        ["id":"invalid", "customer":" ", "amount_cents":999, "status":"paid"],
        ["id":"negative", "customer":"A", "amount_cents":-1, "status":"paid"]]
    let gross = amounts.reduce(0,+)
    // Quotient/remainder reference exercises rounding without matching the worker formula.
    let fee = amounts.reduce(0) { $0 + ($1 * bps) / 10000 + (($1 * bps) % 10000 >= 5000 ? 1 : 0) }
    let result: [String: Any] = ["customers":[
        ["customer":"A", "gross_cents":gross, "refund_cents":999, "fee_cents":fee, "net_cents":gross-999-fee, "count":amounts.count+1],
        ["customer":"B", "gross_cents":0, "refund_cents":5, "fee_cents":0, "net_cents":-5, "count":1]],
        "accepted":amounts.count+2, "duplicates":1, "ignored":2, "rejected":2,
        "gross_cents":gross, "refund_cents":1004, "fee_cents":fee, "net_cents":gross-1004-fee]
    try add(["op":"invoice", "fee_bps":bps, "events":events], result)
    raw("{", invalid)
    try add(invoiceRequest, invoiceResult)
    try add(["op":"invoice", "fee_bps":bps, "events":[]], ["customers":[], "accepted":0, "duplicates":0, "ignored":0, "rejected":0, "gross_cents":0, "refund_cents":0, "fee_cents":0, "net_cents":0])
    try add(["op":"invoice", "fee_bps":bps, "events":events], result)
}
for fee in ["null", "true", "-1", "1001", "1.5", "\"250\""] {
    raw("{\"op\":\"invoice\",\"events\":[],\"fee_bps\":\(fee)}", invalid)
}
raw(#"{"fee_bps":null,"op":"telemetry","samples":[1],"window":1,"threshold":0}"#, ["count":1,"min":1,"max":1,"above":1,"weighted_checksum":1])

// Exercise selection with ties and ordered inputs, including exact p95 boundaries.
for n in [1,19,20,21,39,40,41,1000,10001] {
    for mode in 0..<4 {
        let durations = (0..<n).map { i in mode == 0 ? i : mode == 1 ? n-i : mode == 2 ? 7 : random(13) }
        let events: [[String:Any]] = durations.map { ["ts_ms":0,"route":" /ties ","status":500,"duration_us":$0,"bytes":1] }
        try add(["op":"access_log","start_ms":0,"end_ms":1,"events":events], ["routes":[["route":"/ties","count":n,"errors":n,"total_bytes":n,"max_us":durations.max()!,"p95_us":durations.sorted()[n-n/20-1]]],"total_count":n,"total_errors":n,"total_bytes":n])
    }
}
for text in ["null", "true", "42", "\"text\"", "{\"op\":\"other\",\"events\":null}", "{\"op\":42,\"samples\":false}"] { raw(text, unknown) }
for text in ["[1,]", "{\"a\":1,}", "01", "1e", "1.", "[true false]", "{}x", "{\"op\":\"telemetry\",\"samples\":[1,],\"window\":1,\"threshold\":0}"] { raw(text, invalid) }
raw(#"{"samples":[-9e0,3.0,2E0],"threshold":0,"window":2,"op":"telemetr\u0079","extra":{"x":[null,true,false,"\uD83D\uDE00"]}}"#, ["count":2,"min":-3,"max":2,"above":1,"weighted_checksum":1])
raw(#"{"op":"invoice","events":[{"id":"\u0061","customer":"\tA\u000b","amount_cents":3,"status":"paid"},{"id":"a","customer":"B","amount_cents":9,"status":"paid"}]}"#, ["customers":[["customer":"A","gross_cents":3,"refund_cents":0,"net_cents":3,"count":1]],"accepted":1,"duplicates":1,"ignored":0,"rejected":0,"gross_cents":3,"refund_cents":0,"net_cents":3])
// A request larger than 100 KiB crosses multiple incremental-read boundaries.
let samples = Array(repeating: 123456, count: 18000)
let m = samples.count - 999 + 1
try add(["op":"telemetry","samples":samples,"window":999,"threshold":123456], ["count":m,"min":123456,"max":123456,"above":0,"weighted_checksum":123456*m*(m+1)/2])
raw("{\"op\":\"telemetry\",\"samples\":[1]", invalid)
try add(invoiceRequest, invoiceResult)
// Last line has no newline.
input.removeLast(input.last == 10 ? 1 : 0)
if input.last == 13 { input.removeLast() }
let inputURL = directory.appendingPathComponent("input.jsonl")
let outputURL = directory.appendingPathComponent("output.jsonl")
try input.write(to: inputURL)
let process = Process()
process.executableURL = root.appendingPathComponent("worker.sh")
process.arguments = [inputURL.path, outputURL.path]
process.currentDirectoryURL = directory
try process.run(); process.waitUntilExit()
check(process.terminationStatus == 0, "Worker failed")
let output = try Data(contentsOf: outputURL)
let lines = output.split(separator:10)
check(lines.count == expected.count, "Wrong output count \(lines.count), expected \(expected.count)")
for (index, line) in lines.enumerated() {
    let actual = try JSONSerialization.jsonObject(with: Data(line)) as! NSDictionary
    check(actual.isEqual(to: expected[index]), "Mismatch at \(index): \(actual) versus \(expected[index])")
}
print("PASS: \(expected.count) responses, randomized reference checks for all three operations; malformed JSON recovery, integer boundaries, CRLF/LF, blank lines, unterminated final line, >100 KiB request, and different working directory.")
