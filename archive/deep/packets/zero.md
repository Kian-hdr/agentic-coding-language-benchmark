The authoritative task is SPEC.md. The OLD packet below describes compiler paths/syntax only; ignore its old single-request run.sh / argument protocol. Implement new build.sh and one persistent worker.sh INPUT_JSONL OUTPUT_JSONL. All task computation and file parsing/serialization in assigned language.

ZERO={ORIGINAL_BENCHMARK_ROOT}/toolchains/zero/bin/zero



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


Persistent bulk-file IO: pinned Zero native has no stdin. Use std.fs.readBytesAt(path,offset,buffer) and retain unfinished line across chunks. Transport-only working chunked source is {ORIGINAL_BENCHMARK_ROOT}/toolchains/zero/deep_io_probe. Never spawn a process per request. Inspect local version-matched std.fs skills.
