# MoonBit: verified setup and evaluation packet

Verified 26 October 2026. Scope: official documentation, installation, toolchain smoke check and continuity assessment. This is not a coding-agent performance result.

## Installed toolchain

Root: `{ORIGINAL_BENCHMARK_ROOT}/toolchains/moonbit`

- `moon 0.1.20261023 (3778465 2026-10-23)`
- `moonc v0.10.17+d971670cd (2026-10-23)`
- `moonrun 0.1.20261023 (3778465 2026-10-23)`
- Native Apple Silicon macOS distribution; stable/default channel.
- Official installer was downloaded and inspected, not executed: it writes shell configuration and uses `$HOME/moonbit.tar.gz`. Instead the same official archives were manually extracted entirely into this task's toolchain directory.
- Download: `https://cli.moonbitlang.com/binaries/latest/moonbit-darwin-aarch64.tar.gz`.
- Official archive SHA-256 matched: `39e02f7730486cea54d12e8e781d83a665f245f6a621d01e17a3a13f104eb437`.
- Core archive SHA-256 (locally recorded, not independently authenticated): `2d837ecbef5933c09726d63682a7695123d622e6aee13525fbc98c4b49433714`.
- Retained `toolchain.tar.gz`, `toolchain.sha256`, `core.tar.gz`, inspected installer, and compiler license in root. This makes the evaluated bytes reproducible. A guessed versioned download path `binaries/0.1.20261023/...` returned 403; do not claim that URL works. Archives downloaded from `latest` were frozen by hash and compiler version.
- Core bundle completed for all stable targets and wasm-gc. No global shell or profile files changed.

## Verified commands

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

## Codex and GPT-6.1 Sol compatibility

Official skills repository explicitly documents installation for Codex, not only Claude. A local checkout is retained in `official_skills`, pinned at commit `8b9f1bad14bc62560dbe3537855379e561a4e066`. No global skills were installed. Relevant skills: `moonbit-orientation`, `moonbit-agent-guide`; the orientation and idioms reference were read for this setup. These provide current API lookup, compiler-error interpretation, test and package guidance. Their presence establishes tooling compatibility, not model training exposure or better GPT-6.1 Sol results.

The normal toolchain is CLI-based, so Codex can read/edit source, query interfaces, check, test and run without VS Code or a MoonBit-specific agent runtime. `moon check --output-json` supports machine-readable diagnostics. Stable targets are wasm, wasm-gc, JavaScript, native; LLVM is nightly-only. Prefer native for this controlled experiment. No verified public GPT-6.1 Sol language-comparative evaluation was found in this bounded research; benchmark results must supply that missing evidence.

Sources: [official skills](https://github.com/moonbitlang/skills), [current documentation](https://docs.moonbitlang.com/en/stable/index.html), [download and verification](https://www.moonbitlang.com/download), [tutorial](https://docs.moonbitlang.com/en/stable/tutorial/tour.html).

## Engineering maturity and continued-support assessment

**Real institutional project, but still a migration risk.** MoonBit was released in August 2023, is led by Zhang Hongbo and developed at IDEA (International Digital Economy Academy). It has a compiler, runtime, build/package system, standard library, VS Code integration, multiple backends, public updates, a registry and official agent skills. These are stronger continuity signals than a small experimental repository. They do not establish a funded support guarantee.

Current maintenance was checked directly against GitHub's API:

- `moonbitlang/moon`: commit `180384595c59d9b03e333d22309120f39cc7f10e`, 2026-10-26 09:35:23 UTC, merged PR #2370.
- `moonbitlang/core`: commit `fa1e48dcc775eaa8c0f141a3998b4b6114c22dfb`, 2026-10-26 08:59:54 UTC.
- Public `moonbitlang/moonbit-compiler`: latest commit `d4ada10d212b5376f7f8bf49cd2fbaa275a395df`, 2025-09-29, although installed compiler is dated October 2026. The source-publication lag is significant when assessing independence from the vendor.

Raw API responses are saved in root (`moon_commit.json`, `core_commit.json`, `compiler_commit.json`). Mainline activity is not proof of support for every release.

The July 2025 roadmap targeted 1.0 in H1 2026; the June 2026 update moved that expectation to Q3. The October 23 compiler is still 0.10.17. Current official descriptions disagree between pre-beta, beta and beta-preview. Report it as **pre-1.0 with actively evolving APIs**, not stable 1.0. Update notes contain syntax deprecations and incompatible changes, so agent documentation must be version matched.

### License and exit cost

Compiler source uses the **MoonBit Public Source License**, not a standard permissive license. README explicitly says generated programs may have the user's chosen license and compiler modifications are allowed for noncommercial purposes. It describes the published compiler as the Wasm backend with more components to follow. Build system is Apache-2.0; this does not make the whole current compiler equivalently forkable. This is a technical dependency-risk observation, not legal advice; use exact license terms for procurement review.

If the vendor ceased support, retained toolchain archives permit reproducing the current build on supported machines, but do not guarantee compatibility with future OS versions or the ability to maintain every compiler backend independently. Exported JavaScript/Wasm or native artifacts are deployment outputs, not equivalent maintainable TypeScript/Python source. Rewriting language-specific source and library usage would still be required. Limit initial adoption to isolated modules behind plain JSON/process/FFI boundaries; retain contract tests and a fallback implementation. Do not migrate an entire existing codebase based on a small benchmark.

I found no verified published multi-year commercial support term, foundation-independent governance guarantee, or funded runway figure in the official sources inspected. Do not substitute employer branding, GitHub stars or prize competitions for those commitments.

Primary sources: [team](https://www.moonbitlang.com/about-us), [compiler/license](https://github.com/moonbitlang/moonbit-compiler), [build system](https://github.com/moonbitlang/moon), [core](https://github.com/moonbitlang/core), [release archive](https://www.moonbitlang.com/updates/), [original 1.0 roadmap](https://www.moonbitlang.com/blog/roadmap), [June 2026 update](https://www.moonbitlang.com/updates/2026/06/08/moonbit-0-10-0-release).
