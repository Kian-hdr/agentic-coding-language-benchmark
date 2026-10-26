# BAML 0.23.0 evaluation packet

Verified 26 October 2026. Scope: current general-purpose BAML language, not the older 0.2xx prompt DSL. No model-agent benchmark conducted by this worker.

## Availability and exact installation

Installed wrapper 0.2.5 and pinned language 0.23.0 on macOS arm64, entirely within `toolchains/baml`. No global shell configuration changed.

```sh
BAML_HOME={ORIGINAL_BENCHMARK_ROOT}/toolchains/baml sh {ORIGINAL_BENCHMARK_ROOT}/toolchains/baml/install.sh --no-modify-path --version 0.23.0
```

Official installer: https://pkg.boundaryml.com/install.sh
It fetches wrapper manifest, validates archive SHA256 and archive paths, installs wrapper, then selects pinned toolchain. Local installer and manifest are saved. Language archive recorded by installer:
https://github.com/BoundaryML/baml/releases/download/baml-language-0.23.0/baml-language-0.23.0-aarch64-apple-darwin.tar.gz

Wrapper: `{ORIGINAL_BENCHMARK_ROOT}/toolchains/baml/bin/baml`
Actual language executable: `{ORIGINAL_BENCHMARK_ROOT}/toolchains/baml/toolchains/0.23.0/bin/baml-cli`
Standalone pack host beside that executable.

Always set BAML_HOME to this local directory. `--version` reports wrapper 0.2.5 and toolchain 0.23.0. Wrapper currently produces an internal-binary warning on most commands; this is stderr and does not corrupt JSON stdout.

CLI telemetry is enabled by default. Disabled only in local BAML_HOME with `baml telemetry disable`; also set `DO_NOT_TRACK=1` on benchmark commands. The pricing page says the tool runs locally and never calls their servers, but official TELEMETRY.md documents anonymous command/version/machine metadata collection and exclusions for source/arguments/secrets. Do not repeat the pricing claim unqualified.

## Codex compatibility

Official `baml agent install` produces both `.claude/skills/baml-core/SKILL.md` and `.agents/skills/baml-core/SKILL.md` and explicitly labels the latter Codex / OpenCode. This was actually run inside `toolchains/baml/smoke`; it touched no global skills. Installed skill metadata pins 0.23.0. Copy this project-local skill to each benchmark workspace if testing officially supported workflow.

The CLI has agent output, precise diagnostics, source/API discovery and symbol search. `baml describe NAME` returns built-in signatures plus full source for ordinary stdlib functions. `baml run -e EXPR` permits immediate checking; `check`, `test`, `fmt`, `pack`, LSP are installed. This demonstrates a real Codex integration path. No retrieved primary source establishes GPT-6.1 Sol-specific optimization, training, or superiority; model compatibility here means tool-and-skill compatibility, not model-specific measured performance. Agent Tries BAML measures agent attempts and skill variants but is not an independently controlled language comparison.

## Benchmark contract: verified exact commands

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

## Engineering maturity, continuity and migration risk

Sources:
- Current repository and Apache-2.0 license: https://github.com/BoundaryML/baml
- Release pinned: https://github.com/BoundaryML/baml/releases/tag/baml-language-0.23.0
- General language/limits: https://boundaryml.com/explore.md
- Official team: https://boundaryml.com/who-are-we
- Investor directory: https://www.ycombinator.com/companies/boundary
- Architecture: https://github.com/BoundaryML/baml/blob/canary/baml_language/ARCHITECTURE.md
- Telemetry: https://github.com/BoundaryML/baml/blob/canary/TELEMETRY.md
- Agent evaluation: https://boundaryml.com/atb and https://boundaryml.com/atb/arena

Positive continuity evidence: YC lists active company, Winter 2023, team size 10, compiler-engineering hiring. Official team page names two founders and six engineering members. Their backgrounds include Google/Microsoft/Amazon/compiler work, but credentials alone do not ensure continuity. GitHub contributor API shows multiple substantial contributors (top counts 1078, 863, 860, 371, 206); this is not one developer's side project, though commit counts cannot establish bus factor or sustainable funding. Source and binary releases continue: stable-channel language 0.23.0 published 26 Oct 2026, preceding nightlies 23–25 Oct, latest 0.23.1 nightly 26 Oct. Exact date data saved in `releases.json` and contributors in `contributors.json`. No verified runway/revenue/budget commitment obtained; do not invent funding amount.

The compiler has an incremental Salsa query architecture, parsing, AST/HIR/TIR/MIR/bytecode stages, VM, tests and LSP. This is real engineering. However documentation explicitly calls language pre-1.0, package manager not yet available, and some reflection/harness features planned. New general-language maturity must not be inferred from adoption of the older prompt DSL. The installed version-specific skill differs from some architecture prose (e.g. new client values vs old client blocks), strengthening the case for local version-matched docs.

Apache-2.0 and distributed source permit continued use/forking if sponsor disappears. Incremental adoption through generated native SDKs lowers exit risk because one function/module can be isolated behind a typed boundary. It does not automatically translate business logic back into TS/Python, and maintaining a Rust compiler/VM fork remains expensive. Recommended experimental adoption: bounded leaf modules with language-neutral JSON interfaces and independent tests. Not yet a basis for wholesale migration of a critical production codebase.
