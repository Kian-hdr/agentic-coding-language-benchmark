# Swift local toolchain packet

Swift 6.4 is installed through Xcode. Do not install dependencies or modify global configuration.

Compiler: `{ORIGINAL_XCODE_APP}/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/swiftc`
Invocation: `xcrun swiftc -O main.swift -o program`
Type check only: `xcrun swiftc -typecheck main.swift`

Use a single `main.swift` file with top-level execution, or multiple files with the entry point named `main.swift`. Foundation is available without third-party packages.

Create executable `./run.sh REQUEST_FILE`:

```sh
#!/bin/sh
set -eu
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if [ ! -x "$here/program" ] || [ "$here/main.swift" -nt "$here/program" ]; then
  xcrun swiftc -O "$here/main.swift" -o "$here/program"
fi
exec "$here/program" "$1"
```

JSON input/output skeleton (replace the echo with assigned behavior):

```swift
import Foundation
let data = try Data(contentsOf: URL(fileURLWithPath: CommandLine.arguments[1]))
let request = try JSONSerialization.jsonObject(with: data) as! [String: Any]
// Compute a JSON-compatible object using Swift logic.
let response: [String: Any] = request
let output = try JSONSerialization.data(withJSONObject: response, options: [.sortedKeys])
FileHandle.standardOutput.write(output)
FileHandle.standardOutput.write(Data([10]))
```

JSON objects cast to `[String: Any]`, arrays to `[[String: Any]]`, `[String]` or `[[Int]]` according to declared schema; integral JSON fields may be cast with `as? Int`. Foundation's Codable/JSONDecoder is another standard option if explicit structs are preferred.

Swift `Int` is signed 64-bit on this host; integer `/` truncates toward zero, division by zero traps and must be handled. Normal arithmetic checks overflow. `Array`, `Dictionary`, `Set`, `.sorted()`, and `.sort()` are standard. Dictionary iteration is not sorted. Empty integer ranges require care: prefer collection `.indices` rather than constructing `0...count-1`.

Strings are Unicode-aware; `Array(text.utf8)` provides bytes for ASCII parsing. `CharacterSet(charactersIn: " \t\r\n\u{000B}\u{000C}")` expresses an explicit ASCII whitespace set. Avoid locale-dependent transformations unless required.

Write exactly one JSON value to stdout. Send diagnostic text to stderr if needed. All task logic belongs in Swift; shell only launches the compiled program.
