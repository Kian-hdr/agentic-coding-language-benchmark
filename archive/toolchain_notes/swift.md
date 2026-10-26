# Swift evaluation packet

Verified 26 October 2026. Swift is a mature general-purpose baseline, not a language specifically designed for AI agents. Its compiler, Foundation, package tooling and CLI are usable by Codex through ordinary terminal execution; no model-specific runtime or provider integration is needed. No GPT-6.1 efficiency claim follows from compatibility alone.

## Local readiness

Existing toolchain, no installation or global changes:

- `xcrun swift --version`: Swift driver 1.168.6, Apple Swift 6.4 (`swiftlang-6.4.0.34.1 clang-2100.3.34.1`).
- Target: `arm64-apple-macosx27.2.0`.
- Compiler: `{ORIGINAL_XCODE_APP}/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/swiftc`.
- Compile: `xcrun swiftc -O main.swift -o program`.
- Type-check: `xcrun swiftc -typecheck main.swift`.
- Use Foundation's `Data`, `JSONSerialization` or `JSONDecoder`/`JSONEncoder`; no third-party application libraries needed.

`toolchains/swift/smoke/main.swift` reads the JSON request from argv[1], parses through Foundation, serializes it with sorted keys and prints one JSON response. `toolchains/swift/smoke/run.sh request.json` builds when missing/stale and executes the binary. The wrapper contains no business logic.

The agent briefing is in `packets/swift.md`. No model runs were performed by this setup task.

## Continued support and capabilities

Swift's official documentation identifies a Core Team, steering groups and specialist workgroups, rather than a single informal maintainer. Its compiler, standard library, core libraries, LLDB and Swift Package Manager are maintained as an ecosystem of public projects. The language and supporting tools have been open source since December 2015 under Apache 2.0 with a Runtime Library Exception. These are strong continuity and forkability signals, not a guarantee against future changes.

Apple-platform integration is substantial: official tools support iOS, macOS, watchOS, tvOS and visionOS. Swift also supplies Linux and Windows development support, with package-manager and SourceKit-LSP support documented across those platforms. Official SDK routes additionally cover Android and WebAssembly; these do not imply SwiftUI or Apple's proprietary frameworks become cross-platform. Embedded Swift has a separate constrained compilation mode. Verify package/framework availability for the actual target before choosing Swift for cross-platform products.

The official platform policy names platform owners and requires pull-request CI for supported platforms. That is stronger maintenance evidence than repository popularity alone. Swift is therefore a much lower discontinuation-risk choice than a young experimental Labs language, particularly for Apple software. However, adopting Foundation or SwiftUI APIs can create platform/API migration costs distinct from the language's license.

## Agent tradeoffs

Strong types, explicit optionals, checked arithmetic and native compiler diagnostics help agents identify mistakes. Foundation's JSON support avoids writing a custom parser for this pilot. Native compilation separates build cost from warmed executable runtime. Generic inference, overload-heavy APIs, Unicode strings, and concurrency rules can add debugging complexity; these must be measured, not assumed beneficial. The pilot's CLI algorithms cannot establish SwiftUI/native-app productivity or large-repository maintenance performance.

## Primary sources

- https://www.swift.org/about/ — language, tooling, licensing, open-source date and governance.
- https://www.swift.org/community/ — community process and contribution routes.
- https://www.swift.org/platform-support/ — development targets, platform ownership and CI obligations.

The published platform table is current source evidence, not proof each listed platform was executed in this local test. Only macOS ARM64 was smoke-tested here.
