import Foundation
let dir = URL(fileURLWithPath: FileManager.default.currentDirectoryPath).appendingPathComponent(".test_artifacts")
let file = dir.appendingPathComponent("benchmark.jsonl")
FileManager.default.createFile(atPath:file.path,contents:nil)
let h = try FileHandle(forWritingTo:file)
var seed: UInt64 = 8431
func random(_ n: Int) -> Int { seed = seed &* 6364136223846793005 &+ 1; return Int((seed >> 32) % UInt64(n)) }
for _ in 0..<32 {
    let events: [[String:Any]] = (0..<4096).map { i in ["id":"id\(random(3000))", "customer":" C\(random(80)) ","amount_cents":random(999999),"status":["paid","refund","pending","void"][random(4)]] }
    let logs: [[String:Any]] = (0..<4096).map { i in ["ts_ms":random(1000),"route":" /route\(random(16)) ","status":random(600),"duration_us":random(10000000),"bytes":random(10000)] }
    let samples = (0..<65536).map { _ in random(20001)-10000 }
    for r: [String:Any] in [["op":"invoice","events":events],["op":"access_log","start_ms":0,"end_ms":900,"events":logs],["op":"telemetry","samples":samples,"window":351,"threshold":31]] {
        try h.write(contentsOf:JSONSerialization.data(withJSONObject:r)); try h.write(contentsOf:Data([10]))
    }
}
try h.close()
