import Foundation

let directory = URL(fileURLWithPath: FileManager.default.currentDirectoryPath)
let fixtures = try JSONSerialization.jsonObject(with: Data(contentsOf: directory.appendingPathComponent("tests.json"))) as! [[String: Any]]
let requestURL = directory.appendingPathComponent("test_request.json")
var checked = 0

func check(_ request: [String: Any], _ expected: [String: Any]) throws {
    try JSONSerialization.data(withJSONObject: request, options: [.sortedKeys]).write(to: requestURL)
    let process = Process()
    process.executableURL = directory.appendingPathComponent("run.sh")
    process.arguments = [requestURL.path]
    let output = Pipe()
    process.standardOutput = output
    try process.run()
    let bytes = output.fileHandleForReading.readDataToEndOfFile()
    process.waitUntilExit()
    guard process.terminationStatus == 0,
          let actual = try JSONSerialization.jsonObject(with: bytes) as? [String: Any],
          NSDictionary(dictionary: actual).isEqual(to: expected) else {
        FileHandle.standardError.write(Data("FAILED request=\(request), expected=\(expected), output=\(String(decoding: bytes, as: UTF8.self))\n".utf8))
        exit(1)
    }
    checked += 1
}

for fixture in fixtures {
    try check(fixture["request"] as! [String: Any], fixture["expected"] as! [String: Any])
}

// Generated arithmetic checks exercise all signs and truncation toward zero.
for numerator in -9...9 {
    for denominator in [-3, -2, 2, 3] {
        try check(["op": "calc", "expr": "(\(numerator))/(\(denominator))"], ["value": numerator / denominator])
    }
}

// Enumerate every DAG with four ordered nodes, with duplicate edges and reversed input order.
let names = ["a", "b", "c", "d"]
let possible = [(0,1), (0,2), (0,3), (1,2), (1,3), (2,3)]
for mask in 0..<64 {
    var edges: [[String]] = []
    for (bit, pair) in possible.enumerated() where mask & (1 << bit) != 0 {
        edges.append([names[pair.0], names[pair.1]])
        edges.append([names[pair.0], names[pair.1]])
    }
    try check(["op": "topo", "nodes": Array(names.reversed()), "edges": edges], ["order": names])
}
print("Passed \(checked) tests")
