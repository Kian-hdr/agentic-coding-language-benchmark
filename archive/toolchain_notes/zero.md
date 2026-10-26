# Zerolang evaluation packet

Research and installation verified 26 October 2026. Scope: published compiler and local smoke tests, not model benchmarks. No global PATH/configuration/skill installation changed.

## Recommendation and Codex compatibility

Zerolang is genuinely designed for coding agents, with a graph as its canonical program, semantic query and patch commands, version-matched documentation, typed diagnostics and native compilation. It is compatible with a Codex terminal workflow because all authoring, checking and execution are CLI operations. No API/model-specific runtime is required to write Zero.

However, there is NO measured GPT-6.1 Sol advantage established here or in the inspected official evaluation documentation. The upstream live harness currently explicitly uses Claude Code, Vercel Sandbox and AI Gateway, defaulting to Claude Opus 4.7 and Sonnet 4.6. This is evidence of testing orientation, not model training or incompatibility with Codex. Read the installed compiler's skills instead of relying on model recollection.

Treat it as an interesting experimental comparator, NOT a prudent broad production migration target. The current repository explicitly warns about breaking changes, rough edges and security issues and calls itself experimental. A concrete checker/build inconsistency was reproduced below.

## Installed and pinned

- Binary: `{ORIGINAL_BENCHMARK_ROOT}/toolchains/zero/bin/zero`
- Version: `zero 0.3.4 (build 5b3a90a)`
- Release: v0.3.4, published 2026-06-13 16:54:57 UTC.
- Tag commit: `5b3a90a7756e48ab449eb16e688044b8decec7a9`.
- macOS ARM64 SHA-256: `f89fe71757484998402caae0cedb9a0a1d9d5311443e35bd4a6c82a34450cd87`.
- Official installer was downloaded and inspected before execution. It downloads the binary and checksum file, verifies SHA-256, and moves only the binary to the explicit install directory. Pinned installation used `ZERO_VERSION=v0.3.4` and project-local `ZERO_INSTALL_DIR`.
- Saved evidence: `toolchains/zero/{install.sh,CHECKSUMS.txt,release.json,release-ref.json,repo.json,commits.json,contributors.json,releases.json}`.
- Current upstream main when inspected: `7e1a64d27cc37671df31c6370890bce86f5135e1`, 2026-09-16, README Labs badge change. Main contains 16 commits after the published release, so main documentation need not exactly match the pinned binary.

## Essential model briefing

Use the absolute binary path, abbreviated `ZERO` below. Do not alter global configuration. Version-matched docs are already saved as `toolchains/zero/agent.txt`, `language.txt`, `stdlib.txt`; obtain additional sections with:

```sh
"$ZERO" skills get graph
"$ZERO" skills get stdlib --topic std.json
"$ZERO" skills get stdlib --topic std.args
```

The checked-in upstream bootstrap skill uses SKILL.md conventions understood by Codex, but the benchmark can load these project-local packets without installing any skill globally.

```sh
"$ZERO" init --template cli /absolute/path/to/project
"$ZERO" query /absolute/path/to/project
"$ZERO" patch /absolute/path/to/project --replace-fn main --body-file - <<'BODY'
let input: String = std.args.getOr(1, "{}")
check world.out.write(input)
check world.out.write("\n")
BODY
"$ZERO" check /absolute/path/to/project
"$ZERO" build --out /absolute/path/to/project/program /absolute/path/to/project
"$ZERO" run /absolute/path/to/project -- '{"hello":"world"}'
"$ZERO" test /absolute/path/to/project
```

`init --template cli` ALREADY creates `main`; following it with the README's `addMain` fails because the function exists. Use `--replace-fn` for the generated body. Qualified stdlib names work directly without explicit imports in this example.

Use `zero.graph` as canonical input. `.0` files are human projections. `zero view --fn main PROJECT` shows a function, `zero patch --op help` lists supported operations, `zero export PROJECT` refreshes readable projections, and `zero import PROJECT` intentionally imports text edits. Do not delete the graph.

For new helpers use a patch file or stdin:

```text
zero-program-graph-patch v1
upsertFunction add
fn add(a: i32, b: i32) -> i32 {
    return a + b
}
end
```

Apply using `zero patch PROJECT --patch-text -`. `--replace-in-fn NAME --old TEXT --new TEXT` handles anchored edits; `zero query --fn NAME --handles` exposes graph handles. Outputs are concise by default; use `--json` only where a parser needs it because full check/build JSON is large.

### JSON benchmark I/O

The published language explicitly has no stdin. Pass raw JSON as argv[1] using a wrapper that reads the requested file, or read the file directly with Zero's std.fs. The following verified wrapper only transports input, with no task logic:

```sh
#!/bin/sh
set -eu
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
request=$(cat -- "$1")
exec {ORIGINAL_BENCHMARK_ROOT}/toolchains/zero/bin/zero run "$here" -- "$request"
```

The smoke copy at `toolchains/zero/smoke/run.sh` uses an equivalent relative binary path. `./run.sh request.json` produced `{"hello":"world"}` on stdout. Compiler notes go to stderr. For larger inputs use file I/O to avoid OS argument-length limits.

Useful exact signatures:

- `std.args.getOr(index: usize, fallback: String) -> String`.
- `std.json.field(input: Span<u8>, key: Span<u8>) -> Maybe<Span<u8>>`.
- `std.json.u32(input: Span<u8>, key: Span<u8>) -> Maybe<u32>`.
- `std.json.string(buffer: MutSpan<u8>, input: Span<u8>, key: Span<u8>) -> Maybe<Span<u8>>`.
- `std.json.writeObject1U32(buffer: MutSpan<u8>, key: Span<u8>, value: u32) -> Maybe<Span<u8>>`.
- `std.json.parse(allocator: Alloc, text: String) -> Maybe<JsonDoc>`.
- Fixed arrays use `var storage: [4096]u8 = [0; 4096]`; bind writable span with `let out: MutSpan<u8> = storage`.
- `Maybe<T>` payload `.value` must follow a `.has` check.
- Runtime integer arithmetic wraps unchecked; use checked arithmetic helpers when needed. Array bounds are checked. Each function's fixed locals are limited to 128 KiB. This is a low-level systems language, not a Python-equivalent dynamic collection environment.

## Verified smoke results and concrete defect

1. Graph CLI template initialization succeeded.
2. Generated hello-world executed and printed `hello from zero`.
3. Main-function graph replacement for JSON argv echo succeeded.
4. Check succeeded with no diagnostics; native build succeeded; output artifact was 16,632 bytes; included test passed (`1 test(s) ok`).
5. File-wrapper JSON input/output succeeded.
6. Doctor reports host darwin-arm64 ready, cross-target toolchains/sysroots missing, plus documentation/PATH warnings. Host native work does not need the absent cross toolchains.

**Checker/build mismatch:** replacing main with `let wrong: i32 = "not an integer"` was accepted by graph patch (exit 0, `validated: check-equivalent`) and `zero check` (exit 0, `ok`). `zero view` confirms that exact mismatched declaration. Build/run then fail with `BLD004: typed graph MIR literal type is unsupported`, actual `String`. Thus patch/check success alone is not dependable completion evidence, even for this simple malformed declaration. Always compile AND execute.

Preserved under `toolchains/zero/invalid_type_repro/`, including graph and `check_result.json`, `build_result.json`, `view_result.json`. The valid echo smoke was restored afterward. This is not proof all type checking is broken, nor a compiler exploit; it is one reproducible published-release inconsistency.

## Continued-support and migration risk

Positive evidence: official Vercel Labs repository; substantial compiler, tests, conformance and native backend; Apache-2.0 source license; downloadable pinned binaries; version-matched offline docs; non-archived public repo. Apache licensing reduces legal lock-in and permits maintaining a fork, but a compiler fork remains expensive engineering.

Negative evidence: explicitly a Labs experiment, pre-1.0 unstable APIs, only roughly five months of public history (repository created 2026-05-15), latest binary release more than four months before inspection. GitHub contributors API reports 1,187 commits for `ctate` and one for `Railly`. Commit counts are not hours or authenticated employment, but clearly show narrow visible maintenance concentration. The latest substantive code commit was 2026-08-31; latest September commit only adds badges. Company hosting is not evidence of a funded multi-year support commitment, commercial support contract, adoption scale or SLA. No such commitment was established from the inspected official sources.

Assessment: HIGH migration/support uncertainty for a core codebase; suitable for isolated evaluation or replaceable experiments. Keep product logic behind language-neutral boundaries if piloting. Do not predict inevitable abandonment, but do not equate Vercel branding with TypeScript/Python-level continuity.

## Primary sources

- https://github.com/vercel-labs/zerolang
- https://github.com/vercel-labs/zerolang/releases/tag/v0.3.4
- https://github.com/vercel-labs/zerolang/blob/main/skills/zero/SKILL.md
- https://github.com/vercel-labs/zerolang/blob/main/evals/README.md
- https://zerolang.app/docs/intro/
- https://api.github.com/repos/vercel-labs/zerolang/contributors?per_page=10
- https://api.github.com/repos/vercel-labs/zerolang/commits?per_page=5
- https://api.github.com/repos/vercel-labs/zerolang/releases/latest

No Codex model benchmark, throughput advantage or production suitability is claimed by these smoke tests.
