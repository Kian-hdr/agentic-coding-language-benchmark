import Foundation

let root = URL(fileURLWithPath: FileManager.default.currentDirectoryPath)
let fixture = root.appendingPathComponent("test_request.json")
var passed = 0

func check(_ request: [String: Any], _ expected: [String: Any]) throws {
    let input = try JSONSerialization.data(withJSONObject: request, options: [.sortedKeys])
    try input.write(to: fixture)
    let process = Process()
    process.executableURL = root.appendingPathComponent("run.sh")
    process.arguments = [fixture.path]
    let pipe = Pipe()
    process.standardOutput = pipe
    try process.run()
    let output = pipe.fileHandleForReading.readDataToEndOfFile()
    process.waitUntilExit()
    guard process.terminationStatus == 0 else { fatalError("Process failed: \(request)") }
    let actual = try JSONSerialization.jsonObject(with: output) as! [String: Any]
    guard NSDictionary(dictionary: actual).isEqual(to: expected) else {
        fatalError("Request: \(request)\nExpected: \(expected)\nActual: \(actual)")
    }
    passed += 1
}

func calc(_ expression: String, _ value: Int) throws {
    try check(["op": "calc", "expr": expression], ["value": value])
}
func calcError(_ expression: String, _ error: String = "syntax") throws {
    try check(["op": "calc", "expr": expression], ["error": error])
}

try check(["op": "ledger", "entries": []], ["accounts": [], "accepted": 0])
try check(["op": "ledger", "entries": [
    ["id": "a", "account": " bank ", "amount": 5],
    ["id": "a", "account": "", "amount": 99],
    ["id": "b", "account": "\tbank\r\n", "amount": -5],
    ["id": "c", "account": "Zoo", "amount": 2],
    ["id": "d", "account": "\u{000B}\u{000C}Alpha\t", "amount": -3],
    ["id": "d", "account": "other", "amount": 8]
]], ["accounts": [
    ["account": "Alpha", "balance": -3, "count": 1],
    ["account": "Zoo", "balance": 2, "count": 1],
    ["account": "bank", "balance": 0, "count": 2]
], "accepted": 4])
try check(["op": "ledger", "entries": [["id": "a", "account": " \t\n\r\u{000B}\u{000C}", "amount": 1]]], ["error": "empty_account"])
try check(["op": "ledger", "entries": [["id": "a", "account": "\u{00A0}", "amount": 0]]], ["accounts": [["account": "\u{00A0}", "balance": 0, "count": 1]], "accepted": 1])
try check(["op": "ledger", "entries": [["id": "a", "account": "a b", "amount": 2147483647], ["id": "b", "account": "a b", "amount": -2147483647]]], ["accounts": [["account": "a b", "balance": 0, "count": 2]], "accepted": 2])

try check(["op": "topo", "nodes": [], "edges": []], ["order": []])
try check(["op": "topo", "nodes": ["b", "a", "C", "_", "10", "2"], "edges": []], ["order": ["10", "2", "C", "_", "a", "b"]])
try check(["op": "topo", "nodes": ["z", "b", "a"], "edges": [["b", "a"], ["b", "a"]]], ["order": ["b", "a", "z"]])
try check(["op": "topo", "nodes": ["a", "b", "c", "d"], "edges": [["a", "c"], ["b", "c"], ["c", "d"]]], ["order": ["a", "b", "c", "d"]])
try check(["op": "topo", "nodes": ["a"], "edges": [["a", "a"]]], ["error": "cycle"])
try check(["op": "topo", "nodes": ["a", "b"], "edges": [["a", "b"], ["b", "a"]]], ["error": "cycle"])
try check(["op": "topo", "nodes": ["a", "b"], "edges": [["a", "b"], ["b", "a"], ["x", "a"]]], ["error": "unknown_node"])
try check(["op": "topo", "nodes": [], "edges": [["x", "x"]]], ["error": "unknown_node"])
try check(["op": "topo", "nodes": ["a"], "edges": [["a", "x"]]], ["error": "unknown_node"])

try calc("-(2 + 3) * 4 / 3", -6)
try calc("1+2*3", 7)
try calc("20 / 3 / 2", 3)
try calc("10 - 3 - 2", 5)
try calc("-7/3", -2)
try calc("7/-3", -2)
try calc("-7/-3", 2)
try calc("1--2", 3)
try calc("-+-+--5", 5)
try calc("\t\n\r\u{000B}\u{000C} + ( 00012 ) ", 12)
try calc("2 * -(3 + -4)", 2)
try calc("2147483647", 2147483647)
try calc("-2147483648", -2147483648)
try calc("(-2147483647-1)/2", -1073741824)
try calc("0", 0)
for expression in ["", " \t", "()", "1+", "*2", "(1", "1)", "(1))", "((1)", "2(3)", "(2)3", "1 2", "1.2", "abc", "1%2", "2**3", "1//2", "-", "++", "1,2", "0x10", "1\u{00A0}+2", "１２", "1+()"] {
    try calcError(expression)
}
for expression in ["1/0", "1/(2-2)", "0/0", "3/-0", "1/(2/3)"] {
    try calcError(expression, "division_by_zero")
}
for a in -8...8 {
    for b in [-3, -1, 1, 3] {
        try calc("(\(a)) / (\(b))", a / b)
        try calc("(\(a)) + (\(b)) * 2", a + b * 2)
    }
}
try check(["op": "other"], ["error": "unknown_op"])
print("Passed \(passed) tests")
