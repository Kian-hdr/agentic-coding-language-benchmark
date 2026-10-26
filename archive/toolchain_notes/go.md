# Go evaluation setup

Verified 26 October 2026. No installed Go found through ordinary Homebrew/local locations or command discovery. Downloaded official **go1.27.3 darwin/arm64** archive and checked its SHA-256 against official Go download JSON: `dd3908cf20959d798c1e06ebe5b72213f0505ce01373b40ce3110975a6cd99c2`. Release selection JSON and archive are retained. Extracted inside the evaluation directory; no system install or shell edits.

Compiler: `{ORIGINAL_BENCHMARK_ROOT}/toolchains/go/go/bin/go`.

Set `GOTOOLCHAIN=local` to prevent implicit toolchain downloads, and `GOCACHE={ORIGINAL_BENCHMARK_ROOT}/toolchains/go/cache` to use prewarmed standard-library compilation. Native compilation and execution of JSON echo succeeded. Starter: `toolchains/go/template`, containing Go module and main. Build `go build -o program main.go`, run `./program '{"probe":42}'`. Standard `encoding/json` supplies protocol parsing; no external dependency needed. Neutral packet: `packets/go.md`.

## Support and migration risk

Go has a public compiler and extensive standard library, a stable Go 1 compatibility policy, long release history, and broad industrial usage. Official policy supports each major release until two newer major releases exist, issuing security and critical bug fixes. Go 1.27.3 was released October 19, 2026 and is the current version from the official download endpoint checked here. Standard Go 1 source programs are intended to continue compiling across Go 1 updates, with documented exceptions for security fixes, compiler bugs and unspecified behavior. This is a tangible compatibility contract, unlike a general promise of continued enthusiasm.

The source is BSD-licensed and independently maintainable under its terms. This lowers discontinuation lock-in relative to a partially available compiler, but corporate involvement does not guarantee indefinite support. Existing application rewrites still cost time, particularly frontend/browser frameworks and Python scientific libraries. Go fits services and command-line tools especially well; using it does not prove superior agent-generation efficiency.

Primary sources:
- https://go.dev/dl/?mode=json (selection saved locally)
- https://go.dev/doc/devel/release
- https://go.dev/doc/go1compat
- https://go.dev/LICENSE
- https://pkg.go.dev/encoding/json
