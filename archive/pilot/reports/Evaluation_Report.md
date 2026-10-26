# Codex GPT-6.1 Sol: programming-language evaluation

Research and local testing: 26 October 2026. This is a bounded pilot, not a universal language leaderboard.

## Decision

The results favor established languages for an existing, long-lived codebase.
Python had the shortest measured authoring time (105.7 seconds for initial
implementation plus the later change, median of two trials). TypeScript followed
at 124.3 seconds and remains the natural web/application choice. Go delivered
the fastest prepared 1,000-entry ledger executable among implementations correct
in both runs (about 3.55 ms including process startup and JSON IO).

All nine passed the original 316 checks each. Larger-input validation was more
discriminating: the six mainstream languages and BAML passed all 10 workload/run
combinations; MoonBit passed 8 and Zerolang 4. Prepared execution removed build
overhead but did not eliminate the observed incorrect MoonBit ordering or Zero
timeouts. These findings concern the generated programs, not theoretical limits
of the languages.

Among the specialized candidates, BAML is a credible isolated experiment and
MoonBit has the broader existing toolchain. Neither demonstrated a compelling
overall reason to migrate from a mainstream language. Zerolang is not a sensible
production migration recommendation on the current evidence.

## What was actually tested

Nine existing languages were used by the actual Codex CLI with the explicitly
selected `gpt-6.1-sol` model and medium reasoning. Each language received two
fresh implementation starts and two subsequent change requests: 36 scored agent
turns in total. Toolchain setup was completed before timed runs. No existing
product codebase was migrated and no new programming language was developed.

The tasks were a deduplicating account ledger, deterministic topological sorting,
and an arithmetic expression parser, followed by interval merging as a later
change. External tests cover normal cases, error precedence, duplicates, empty
inputs, ASCII whitespace, operator precedence, truncating division and regressions.
Each run has 69 initial checks and 89 post-change checks. The latter repeat the
69 original checks, so 316 observations per language are not 316 independent tasks.

Rust uses pre-vendored serde_json and Kotlin uses preinstalled org.json solely
for JSON transport. Other languages use their standard libraries. Neutral
language packets provide current commands and API discovery. All task logic
was written by the tested model in the assigned language. A separate source
and command-log review found no obvious outsourcing of business logic or
cross-run answer copying across both rounds. See [Compliance_Review.md](Compliance_Review.md).

## Measured authoring results

Creation + change time is the median of the two trial totals. Some agent calls
ran concurrently, so this includes queueing, network and tool latency, not
only reasoning or compiler work. Differences with two samples should not be
treated as statistically established language effects.

Input and output totals below cover all four scored turns for each language.
Uncached input is reported input minus reported cached input; cached input is
not free and remains in the raw JSON. Nonzero commands include failed shell
commands and exploratory lookups, not just compiler errors. No dollar-cost
estimate is made.

| Language | Passed checks | Median creation + change | Uncached input | Output | Nonzero commands |
|---|---:|---:|---:|---:|---:|
| Python | 316/316 | 105.7 s | 102.1 kTok | 10.4 kTok | 0 |
| TypeScript | 316/316 | 124.3 s | 102.8 kTok | 12.5 kTok | 0 |
| Rust | 316/316 | 148.7 s | 94.1 kTok | 11.2 kTok | 2 |
| Kotlin | 316/316 | 154.6 s | 93.1 kTok | 12.2 kTok | 1 |
| BAML | 316/316 | 157.7 s | 155.9 kTok | 14.4 kTok | 5 |
| MoonBit | 316/316 | 171.2 s | 129.0 kTok | 15.0 kTok | 3 |
| Go | 316/316 | 186.0 s | 95.2 kTok | 18.8 kTok | 5 |
| Swift | 316/316 | 188.5 s | 93.4 kTok | 14.1 kTok | 3 |
| Zerolang | 316/316 | 505.1 s | 186.8 kTok | 35.7 kTok | 20 |

Full counters, per-phase results and both trial timings: [summary.json](results/summary.json).
Original source, exact prompts and complete JSONL tool events are under [runs/](runs/).
Initial and post-change source snapshots are retained under [snapshots/](snapshots/).

## Larger inputs and process performance

After agent work finished, each generated program ran sequentially on ledger
inputs of 100, 1,000 and 5,000 entries, a 100-node graph, and 1,000 intervals.
Every workload uses one warm-up and five measured executions when successful.
The times include the generated launcher, process startup, JSON transport and
any rebuild/check the launcher chooses to do. They are not isolated algorithm
throughput or proof that one compiler intrinsically produces faster programs.
Ten workload/trial combinations exist per language. A failed combination stops
further repetitions of that combination, preserving its diagnostic.

| Language | Delivered launcher: ledger 1,000 | Prepared executable: ledger 1,000 | Larger-workload checks passed |
|---|---:|---:|---:|
| Python | 28.89 ms | 31.19 ms | 10/10 |
| TypeScript | 77.02 ms | 53.51 ms | 10/10 |
| Go | 11.99 ms | 3.55 ms | 10/10 |
| Rust | 13.66 ms | 4.35 ms | 10/10 |
| Swift | 17.95 ms | 7.14 ms | 10/10 |
| Kotlin | 73.65 ms | 58.08 ms | 10/10 |
| MoonBit | 44.71 ms (1/2 correct) | 3.42 ms (1/2 correct) | 8/10 |
| BAML | 117.12 ms | 100.79 ms | 10/10 |
| Zerolang | failed | failed | 4/10 |

Complete timings and failure diagnostics: [runtime_performance.json](results/runtime_performance.json).

A second comparison uses the same source with prepared executables: release
builds for Rust and MoonBit, packed BAML, and direct existing binaries for the
others. It removes wrapper/rebuild overhead without modifying business logic.
It still includes process startup and JSON handling, not steady-state server
throughput. Prepared tests use the 1,000-entry ledger, 100-node graph and 1,000
intervals; oversized argv transport can otherwise obscure the comparison.
[Prepared timings and build commands](results/prepared_performance.json).

Larger-input failures are failures of these particular generated implementations
and launchers. They must not be promoted to inherent language size limits.
In particular, a raw-JSON command-line argument can hit OS transport limits
where a file-reading implementation would work.

The larger inputs exposed a specific MoonBit trial-one defect: the generated
code used default string sorting, while MoonBit intentionally uses shortlex
(length first) rather than lexicographical ordering. The other MoonBit trial
explicitly selected lexical comparison and passed. Additional two-case sorting
probes across all languages are in [sorting_probe.json](results/sorting_probe.json).
An independent source check and native probe confirmed the documented semantics:
[MoonBit String implementation](https://github.com/moonbitlang/core/blob/main/builtin/string.mbt).
This is an implementation mistake relative to the task, not a compiler bug.

## Compiler-validation probe

An additional, separate probe assigned a string to an explicitly numeric local.
TypeScript, Rust, Go, Swift, Kotlin, MoonBit and BAML rejected the mismatch.
Python's ordinary compiler accepted its annotation, as expected for dynamic
typing; this was not counted as a Python defect. Zerolang 0.3.4 accepted its
graph patch and `check`, while native compilation rejected it. That is a
reproduced checker/build inconsistency for this case, not proof of a memory
safety failure or a judgment about every Zero program.

Exact commands and diagnostics: [type_validation.json](probes/type_validation.json).

## Codex compatibility and model training

Successful implementation and execution is direct evidence that all tested
languages can be used through Codex's terminal workflow. It does not establish
equal ease of use, nor that any model was trained specifically for the language.
No examined primary source established special GPT-6.1 Sol training or a
vendor-guaranteed GPT-6.1 performance advantage for the three agent-oriented
languages.

MoonBit and BAML have official Codex-compatible skills. Zerolang provides
version-matched CLI skills; its inspected upstream agent evaluation uses Claude
Code. A vendor's choice of demonstration model is not a compatibility limit.
The current test used Codex, not those vendor-specific agent harnesses or an
inference-time constrained sampler. In particular, benefits from MoonBit's
published semantics-aware decoder cannot automatically be attributed to a
normal Codex CLI run.

- [Official Codex command reference](https://learn.chatgpt.com/docs/developer-commands)
- [MoonBit skills](https://github.com/moonbitlang/skills)
- [BAML setup](https://developer.boundaryml.com/baml/get-started)
- [Zerolang agent evaluation](https://github.com/vercel-labs/zerolang/blob/main/evals/README.md)

## Continued support and migration risk

These are qualitative comparisons of evidence, not probabilities of survival.

| Language | Continuity evidence | Main adoption consideration |
|---|---|---|
| Python | PSF stewardship, broad open ecosystem, published supported release branches | Strong general automation/data choice; add runtime validation and suitable static checking for larger systems |
| TypeScript | Microsoft-led public compiler and JavaScript ecosystem/interoperability | Strong app/web default; static types do not validate arbitrary runtime inputs |
| Go | Public compiler/stdlib and explicit Go 1 source compatibility policy | Strong service/CLI choice; narrower UI/data-library fit than TS/Python |
| Rust | Multi-team project governance, foundation support, public compiler and stable editions | Strong systems/safety choice; ownership and build ecosystem add complexity |
| Swift | Public core team, steering/workgroups, Apple ecosystem investment and platform CI | Preferred for native Apple applications; framework portability differs from language portability |
| Kotlin | JetBrains investment, multi-organization foundation and compatibility governance, JVM interoperability | Preferred for Android/JVM work; this pilot tests JVM CLI, not Android UI |
| MoonBit | Active IDEA team, full toolchain, current core/build work | Pre-1.0; custom compiler license and public compiler source lag weaken independent fallback options |
| BAML | Active BoundaryML team, frequent releases, Apache-2.0 compiler/runtime source, host-language bridges | New general-purpose language remains pre-1.0; old prompt-DSL adoption does not prove the replacement mature |
| Zerolang | Real Vercel Labs compiler, tests, published binaries and Apache-2.0 source | Explicit experiment, concentrated visible maintenance and older release; high uncertainty for wholesale migration |

MoonBit's build system and core had recent commits, but the inspected public
compiler source lagged the installed binary. Its custom SSPL-derived license
distinguishes user programs from compiler modification rights. Retaining the
binary preserves a build environment, not indefinite maintainability.

BAML has multiple substantial contributors and an active company listing, but
no verified multi-year support promise or financial runway was found. Its
Apache license and bridges offer a clearer incremental/fork path than a partly
published compiler. Those reduce lock-in; they do not remove rewriting costs.

Zerolang's organization branding does not establish a commercial support
commitment. The inspected contributor history was heavily concentrated in one
account. Its source license makes a fork legally feasible under its terms, but
maintaining a compiler remains substantial work.

Evidence and exact versions are in [docs/](docs/); installation archives and
source metadata are retained under [toolchains/](toolchains/).

### Primary support sources

- [Python stewardship](https://www.python.org/psf/about/) and [release support](https://www.python.org/downloads/)
- [TypeScript compiler](https://github.com/microsoft/TypeScript)
- [Go compatibility](https://go.dev/doc/go1compat)
- [Rust governance](https://rust-lang.org/governance/)
- [Swift governance](https://www.swift.org/about/) and [platform support](https://www.swift.org/platform-support/)
- [Kotlin foundation](https://kotlinfoundation.org/structure/) and [FAQ](https://kotlinlang.org/docs/faq.html)
- [MoonBit compiler and license](https://github.com/moonbitlang/moonbit-compiler)
- [BAML source](https://github.com/BoundaryML/baml) and [team](https://boundaryml.com/who-are-we)
- [Zerolang source and experimental status](https://github.com/vercel-labs/zerolang)

## How to use this result

Keep measured authoring efficiency distinct from native execution speed,
expressiveness, platform fit and long-term support. A small CLI pilot is not a
sound reason to rewrite a functioning product in another language. For a new
product, match its primary platform: TypeScript for web applications, Python for
automation/data work, Go for small services/CLIs, Rust for systems requiring
low-level control, Swift for Apple UI, and Kotlin for Android/JVM.

MoonBit and BAML merit isolated experiments behind portable interfaces. The
evidence does not establish that adopting either will make a long-lived codebase
more reliable than a well-supported mainstream stack. Zerolang should remain
an experimental comparator rather than a production foundation at this stage.

Detailed limitations and changes to the pilot: [METHODOLOGY.md](METHODOLOGY.md).
Frozen tasks: [BENCHMARK.md](BENCHMARK.md).

## Versions evaluated

- Python: 3.14.7
- TypeScript: 7.0.2 / Node 26.0.0
- Go: 1.27.3
- Rust: 1.99.1
- Swift: 6.4
- Kotlin: 2.4.21 / JDK 21.0.12.1
- MoonBit: moonc 0.10.17 / moon 0.1.20261023
- BAML: Language 0.23.0 / wrapper 0.2.5
- Zerolang: 0.3.4

Accuracy: 88% | Evidence: strong | Main uncertainty: small workload sample and future support
