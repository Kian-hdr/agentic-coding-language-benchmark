BAML_HOME={ORIGINAL_BENCHMARK_ROOT}/toolchains/baml; set DO_NOT_TRACK=1.
Official syntax skill: {ORIGINAL_BENCHMARK_ROOT}/toolchains/baml/smoke/.agents/skills/baml-core/SKILL.md
 verified exact commands

The simplest fair file-to-JSON contract needs no Python/TypeScript bridge. BAML can natively read files, parse JSON, compute and return typed values.

Smoke source (`toolchains/baml/smoke/baml_src/main.baml`):

```baml
class Request { values: int[] }
class Reply { total: int }
function main(path: string) -> Reply {
  let request = baml.json.decode<Request>(baml.fs.read(path));
  Reply { total: request.values.reduce((acc, n) -> { acc + n }, 0) }
}
```

`request.json` contains `{"values":[1,2,3]}`. Actual command:

```sh
BAML_HOME={ORIGINAL_BENCHMARK_ROOT}/toolchains/baml DO_NOT_TRACK=1 {ORIGINAL_BENCHMARK_ROOT}/toolchains/baml/bin/baml --directory {ORIGINAL_BENCHMARK_ROOT}/toolchains/baml/smoke run main --output-format json -- --path {ORIGINAL_BENCHMARK_ROOT}/toolchains/baml/smoke/request.json
```

Exit 0; stdout exactly `{"total":6}`. Hello-world scaffold also ran and returned `"hello from baml"`.

For benchmark workspace `run.sh`, use an exec-only wrapper resolving its own directory, setting local BAML_HOME / DO_NOT_TRACK, then `baml --directory "$dir" run main --output-format json -- --path "$1"`. Main receives the request filename and all parsing/computation is BAML. Ensure caller gives absolute request paths or normalize in wrapper without modifying data.

Packing verified:

```sh
BAML_HOME={ORIGINAL_BENCHMARK_ROOT}/toolchains/baml DO_NOT_TRACK=1 {ORIGINAL_BENCHMARK_ROOT}/toolchains/baml/bin/baml --directory {ORIGINAL_BENCHMARK_ROOT}/toolchains/baml/smoke pack main --output {ORIGINAL_BENCHMARK_ROOT}/toolchains/baml/smoke/smoke_cli
{ORIGINAL_BENCHMARK_ROOT}/toolchains/baml/smoke/smoke_cli --path {ORIGINAL_BENCHMARK_ROOT}/toolchains/baml/smoke/request.json
```

Again exit 0, same JSON. Standalone output defaults to JSON. Fair runtime benchmarks should compare packaged program separately from `baml run` startup/compiler time.

Alternative native stdin protocol: a typed `main(request: Request)` gets a generated CLI supporting `--json-args -` (stdin), `--json-args @file`, or inline JSON. Wrapper envelope must be `{"request":{...}}`. `baml.io.input(null)` reads one line, strips newline, returns empty string at EOF. `baml.fs.read(path)` is more robust for multi-line JSON files. The file protocol above is preferred for matched tasks.

`baml check` succeeds but prints multiple unreachable-code warnings in built-in CSV/iterator/stream/MCP modules even for the tiny source; these are observed toolchain warnings, not benchmark-author code defects. Runs print formatting warnings until `baml fmt` is run.

## Compact language notes for the coding agent

Use the installed official skill for complete current syntax. Important traps relative to TypeScript:

- `function f(x: int) -> int { x + 1 }`, expression blocks return final expression without semicolon; `return x;` for early exit.
- Class fields `name: type,`; construction `Reply { total: n }`; classes are reference types, mutable fields.
- `int`, `float`, `string`, `bool`, `T?`, `T[]`, `map<string,T>`. No unchecked `any` casts.
- `int/int` truncates, unlike TypeScript. Convert to float for fractional division.
- `let` reassignable; `const` global immutable binding. Loops `for (let item in items)` and `while (cond)`.
- No ternary. `if (cond) { x } else { y }` is an expression.
- `.length()`, `.to_string()`, `.to_lower_case()` and other snake_case stdlib methods. Read API instead of guessing.
- `.map((x) -> { ... })`, `.reduce((a,b) -> { ... }, initial)`. `.sort_by_key` mutates receiver and returns it.
- Map `.get(key)` returns optional; `(m.get(k) ?? 0) + 1`; `.set(k,v)` mutates.
- `baml.json.decode<Request>(raw)` validates schema, `baml.json.stringify(value)` produces JSON. `baml.json.json` supports dynamic JSON when needed; inspect `baml describe baml.json`.
- Named function call parameters use `=`, never `:`. Defaulted params must be passed by name.
- `test "name" { assert.equal(actual, expected) }` supports pure deterministic unit tests with no model calls.
- `baml describe String`, `Array`, `Map`, `baml.json`, `baml.fs`, `baml.math` supplies current built-in docs.

