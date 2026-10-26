The authoritative task is SPEC.md. The OLD packet below describes compiler paths/syntax only; ignore its old single-request run.sh / argument protocol. Implement new build.sh and one persistent worker.sh INPUT_JSONL OUTPUT_JSONL. All task computation and file parsing/serialization in assigned language.

MoonBit root: {ORIGINAL_BENCHMARK_ROOT}/toolchains/moonbit



Set these within each command or process; do not edit the user's global environment:

```sh
export MOON_HOME={ORIGINAL_BENCHMARK_ROOT}/toolchains/moonbit
export PATH="$MOON_HOME/bin:$PATH"
moon version --all
moon new /absolute/path/to/project
moon -C /absolute/path/to/project check
moon -C /absolute/path/to/project run --quiet --target native cmd/main -- '{"probe":42}'
moon -C /absolute/path/to/project build --target native
moon -C /absolute/path/to/project test
moon -C /absolute/path/to/project fmt
moon -C /absolute/path/to/project ide doc '@json'
moon -C /absolute/path/to/project ide doc '@env'
```

`moon new` currently generates `moon.mod` and `moon.pkg` (new syntax), not the older JSON configurations. Default generated module `username/smoke`; username warning is harmless, no login needed. The template's test command discovered **zero tests**; no claim of meaningful test-suite success is made.

Verified smoke project: `$MOON_HOME/smoke`. Hello-world check/run succeeded. Then main was replaced with a JSON round-trip probe; check, native compile and JSON output succeeded. Native artifact: `smoke/_build/native/debug/build/cmd/main/main.exe`.

`smoke/run.sh smoke/request.json` prints exactly `{"probe":42}` on stdout. The runner reads a request file with the shell, passes raw JSON as one argument to MoonBit, and builds/runs native. It is permitted benchmark plumbing, not candidate business logic. For execution-only timing, prebuild and run `main.exe "$JSON"` to exclude compiler time.

## Minimum benchmark implementation guide

In `cmd/main/moon.pkg`:

```text
import {
  "moonbitlang/core/env",
  "moonbitlang/core/json",
}
pkgtype(kind: "executable")
```

In `cmd/main/main.mbt` (verified):

```moonbit
///|
fn main {
  let args = @env.args()
  let request = @json.parse(args[1]) catch {
    _ => panic()
  }
  println(request.stringify())
}
```

Implement business logic in MoonBit and preserve the request/result contract provided by the benchmark. Core packages do not need dependency installation. `@json.parse` raises `ParseError`. Avoid inventing JavaScript/Rust-like APIs: discover exact signatures using `moon ide doc`. `Int` is 32-bit here; select Int64 or Double deliberately to match benchmark numeric requirements. JSON API uses `Json` with constructors `Json::array`, `Json::object`, `Json::string`, `Json::number`, `Json::boolean`, `Json::null`; typed decoding is available as `@json.from_json` for `FromJson` types and encoding through `@json.to_json`/`ToJson`. A full verified interface snapshot is `json_api.txt` in the toolchain directory. JSON parsing rejects lone UTF-16 surrogate escapes; don't accidentally count a cross-language Unicode-semantics difference as algorithm failure.



# BAML and MoonBit: sustained IO readiness

26 October 2026. Version-local CLI/source inspection plus IO-only smoke tests. No workload/business logic or model-agent trials implemented here. Owned probe: `toolchains/baml/deep_io_probe`.

## Ready-to-run persistent smoke executables

Both executables open input/output once, parse and serialize each line inside one process, and write one JSON value per input line. They preserve order. Verified three-line input including a 70 KB line across a buffer boundary, UTF-8 text, signed int64 endpoints and a final unterminated line. JSON values matched exactly after independent decoding. This is IO correctness evidence, not performance measurement.

BAML:

```sh
{ORIGINAL_BENCHMARK_ROOT}/toolchains/baml/deep_io_probe/worker --input INPUT_JSONL --output OUTPUT_JSONL
```

The packed CLI prints `null` to stdout for a void return; output file itself contains exactly JSONL. An exec-only wrapper can map positional `./worker INPUT OUTPUT` to `--input "$1" --output "$2"` and redirect stdout to `/dev/null`. Diagnostics should stay on stderr.

MoonBit:

```sh
{ORIGINAL_BENCHMARK_ROOT}/toolchains/baml/deep_io_probe/moonbit/_build/native/release/build/cmd/main/main.exe INPUT_JSONL OUTPUT_JSONL
```

No stdout from this smoke. Source files in each probe contain transport/parse/stringify only.

## BAML 0.23.0 exact supported APIs

Verified with installed `baml describe`, not old prompt-DSL documentation:

```text
baml.fs.open(path: string, mode: "r"|"r+"|"w"|"w+"|"a"|"a+") -> File
File.read(limit: int) -> uint8array?       // null means EOF
File.write(data: string|uint8array) -> int // writes all data
File.close() -> null
File.flush() -> null                     // Write interface
uint8array.concat(other) -> uint8array
uint8array.index_of(item: int) -> int?
uint8array.slice(start: int,end: int) -> uint8array
string.from_utf8(bytes) -> string         // strict UTF8
baml.json.parse(text) -> json
baml.json.decode<T>(text) -> T
baml.json.stringify(value) -> string
```

BAML has no discovered buffered line-reader, so smoke reads 65,536-byte chunks, carries pending bytes across reads, searches LF and decodes complete lines. EOF processes remaining nonempty bytes. Memory is bounded by chunk plus longest line and parsed request, not total input file. `slice`/`concat` allocate; benchmark authors may improve buffer design. A very long individual line necessarily needs policy (maximum size or proportional memory). Do not use `fs.read`, `File.text`, or `File.bytes` to load the whole JSONL workload.

Open files once and use `defer { handle.close(); }`. Keep request processing state inside the per-line function. Maps/classes are shared reference types, so avoid retaining request objects through top-level globals or closures unless the workload explicitly calls for persistent state.

Native packaging (same pinned local environment as pilot):

```sh
BAML_HOME={ORIGINAL_BENCHMARK_ROOT}/toolchains/baml DO_NOT_TRACK=1 {ORIGINAL_BENCHMARK_ROOT}/toolchains/baml/bin/baml --directory PROJECT pack main --output PROJECT/worker
```

Packed smoke compile/run succeeded. This embeds BAML bytecode with native runtime; do not describe it as the business functions compiled to optimized machine code comparable to Rust native code.

Numeric caveat: BAML `int` is **signed 63-bit**, -2^62 through 2^62-1, because of runtime tagging. Full signed int64 requires `bigint`; it has arbitrary precision, `42n` literals, `bigint.parse(string)` and `.to_int()` checked narrowing. `map<string,bigint>` works, with `.get`, `.set`, `.has`, `.clear`, `.keys`, `.values`. Map iteration preserves insertion order. Both `baml.json.decode<map<string,bigint>>(raw)` and JSON serialization of max-int64 bigint map were locally verified. JSON emits numeric digits, not a quoted string. No numeric computation should pass through float.

## MoonBit native and official async 0.22.5

Compiler remains installed moonc 0.10.17 / moon 0.1.20261023. Native core does not provide the full filesystem API used here. Installed **official** `moonbitlang/async@0.22.5` only into the probe subproject; package download is setup, not agent authoring time. Library source calls itself experimental and warns APIs may change. Pin version.

Project setup:

```sh
MOON_HOME={ORIGINAL_BENCHMARK_ROOT}/toolchains/moonbit {ORIGINAL_BENCHMARK_ROOT}/toolchains/moonbit/bin/moon -C PROJECT add moonbitlang/async@0.22.5
```

`cmd/main/moon.pkg` imports `moonbitlang/core/env`, `moonbitlang/core/json`, `moonbitlang/async`, `moonbitlang/async/fs`, `moonbitlang/async/io`; set `supported_targets = "+native"`, `pkgtype(kind: "executable")`.

Locally compiled transport structure:

```moonbit
async fn main {
  let args = @env.args()
  let input = @fs.open(args[1], mode=ReadOnly)
  defer input.close()
  let output = @fs.open(args[2], mode=WriteOnly, create_mode=CreateOrTruncate)
  defer output.close()
  let buffered = @io.BufferedWriter::new(output, size=65536)
  while input.read_until("\n") is Some(line) {
    let value = @json.parse(line)
    buffered.write(value.stringify())
    buffered.write("\n")
  }
  buffered.flush()
}
```

`read_until` consumes separator but excludes it from returned String, returns final unterminated segment, then None. It buffers input incrementally. `File.read(FixedArray[Byte], offset?, max_len?) -> Int32` and `read_some(max_len?) -> Bytes?` are alternatives. The library also has native stdin/stdout under `moonbitlang/async/stdio`.

Build outside measurement:

```sh
MOON_HOME={ORIGINAL_BENCHMARK_ROOT}/toolchains/moonbit PATH={ORIGINAL_BENCHMARK_ROOT}/toolchains/moonbit/bin:$PATH {ORIGINAL_BENCHMARK_ROOT}/toolchains/moonbit/bin/moon -C PROJECT build --target native --release
```

Run `PROJECT/_build/native/release/build/cmd/main/main.exe INPUT OUTPUT`. This was actually built against pinned async 0.22.5, not merely inferred from latest website docs.

MoonBit has true `Int64` and `Map[String,Int64]`. Important JSON boundary trap: built-in `FromJson for Int64` expects a **JSON string**, and `ToJson for Int64` emits a **JSON string**. If the benchmark specifies JSON numbers, implement explicit conversion. Public import `moonbitlang/core/string`, alias @string, exposes `@string.parse_int64(StringView, base?) -> Int64 raise`. After ensuring input is a JSON Number, its `.stringify()` retains original numeric representation for large integers. Numeric output can use `Json::number(n.to_double(), repr=n.to_string())`; its repr emits original decimal digits. Do not trust the Double payload for exact int64 arithmetic, and do not blindly derive FromJson/ToJson for those fields. Version-local relevant sources are `lib/core/json/from_json.mbt`, `lib/core/builtin/json.mbt`, `lib/core/string/pkg.generated.mbti`. Numeric encoding guidance here is based on those signatures/source; only dynamic JSON roundtrip was smoke-tested.

## Request isolation and diagnostic protocol guidance

Separate persistent-process overhead from state leakage. For stateless operations, issue A, B, A and compare both A outputs; add malformed then valid input if the protocol requires per-request recovery. For stateful service semantics, include explicit reset/health operations defined identically across languages. Test reset correctness rather than restarting a process invisibly. Keep input/output counts and sequence identifiers in the outside evaluator. Put diagnostics exclusively on stderr; do not mix time/memory data with result JSON. Measure one persistent process over the whole file, recording startup separately and peak RSS, and make clear that total wall time includes parsing, IO and output formatting. These are suggestions for the root's test design, not implemented workload logic.

## Real HTTP support versus worker surrogate

BAML installed stdlib has actual `baml.http.Server.bind(addr) -> Server`, `.serve(handler, ...)`, Request/Response, TCP/UDP, TLS config, HTTP1/HTTP2 selection, max-body size, max-connections and header timeout. Handler signature returns Response and `throws never`, so errors must be mapped into responses. Its docs call it a minimal HTTP/HTTPS server. API inspection does not establish production operations, framework breadth or load-test reliability.

MoonBit official async 0.22.5 includes actual HTTP server/client, WebSocket and socket support. `@http.Server(@socket.Addr::parse(addr))`; `Server.run_forever(async (Request,&Reader,ServerConnection)->Unit, allow_failure?,max_connections?)`; response/body stream methods, TLS package. An installed `examples/http_server_benchmark` provides a real server example. The whole async library remains experimental. No HTTP server was launched or benchmarked here.

A JSONL worker can test sustained computation, IO and state isolation. It does **not** test HTTP parsing, connection reuse, concurrency, cancellation, routing, TLS, backpressure, authentication or service deployment. Label it a persistent worker benchmark, not a full HTTP/service benchmark.

Primary upstream routes: https://github.com/BoundaryML/baml ; https://github.com/moonbitlang/async ; https://mooncakes.io/docs/moonbitlang/async ; https://github.com/moonbitlang/core . Installed version-local sources and smoke artifacts are retained with the probe.

Ready transport starter: {ORIGINAL_BENCHMARK_ROOT}/toolchains/baml/deep_io_probe/moonbit. Copy selected moon.mod/moon.pkg/cmd files and symlink its .mooncakes folder into your project; exclude .git, AGENTS.md, _build. Offline dependency async@0.22.5 is staged. Use explicit lexical_compare for all ASCII alphabetical ordering.
