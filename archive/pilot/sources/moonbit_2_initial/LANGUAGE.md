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

