import json
import statistics
from pathlib import Path

ROOT=Path(__file__).resolve().parent
rows=json.loads((ROOT/'results/summary.json').read_text())
if any(r.get('complete_trials')!=2 for r in rows):
    raise SystemExit('All scored trials must finish before final report generation')
runtime=json.loads((ROOT/'results/runtime_performance.json').read_text())
prepared=json.loads((ROOT/'results/prepared_performance.json').read_text())
names={'python':'Python','typescript':'TypeScript','go':'Go','rust':'Rust','swift':'Swift','kotlin':'Kotlin','moonbit':'MoonBit','baml':'BAML','zero':'Zerolang'}
versions={'python':'3.14.7','typescript':'7.0.2 / Node 26.0.0','go':'1.27.3','rust':'1.99.1','swift':'6.4','kotlin':'2.4.21 / JDK 21.0.12.1','moonbit':'moonc 0.10.17 / moon 0.1.20261023','baml':'Language 0.23.0 / wrapper 0.2.5','zero':'0.3.4'}
table=['| Language | Passed checks | Median creation + change | Uncached input | Output | Nonzero commands |', '|---|---:|---:|---:|---:|---:|']
for r in sorted(rows,key=lambda r:r['median_total_agent_seconds']):
    usage_note='' if r['usage_complete'] else ' (partial)'
    table.append(f"| {names[r['language']]} | {r['passed']}/{r['planned']} | {r['median_total_agent_seconds']:.1f} s | {r['total_uncached_input_tokens']/1000:.1f} kTok{usage_note} | {r['total_output_tokens']/1000:.1f} kTok{usage_note} | {r['failed_commands']} |")
runtime_table=['| Language | Delivered launcher: ledger 1,000 | Prepared executable: ledger 1,000 | Larger-workload checks passed |','|---|---:|---:|---:|']
for r in rows:
    rs=[x for x in runtime if x['language']==r['language']]
    sample=[x['median_seconds'] for x in rs if x['workload']=='ledger_1000' and x['status']=='pass']
    timing=f'{statistics.median(sample)*1000:.2f} ms' + (f' ({len(sample)}/2 correct)' if len(sample)<2 else '') if sample else 'failed'
    ps=[x['median_seconds'] for x in prepared if x['language']==r['language'] and x.get('workload')=='ledger_1000' and x.get('ok') and x.get('median_seconds') is not None]
    prepared_time=f'{statistics.median(ps)*1000:.2f} ms' + (f' ({len(ps)}/2 correct)' if len(ps)<2 else '') if ps else 'failed'
    runtime_table.append(f"| {names[r['language']]} | {timing} | {prepared_time} | {sum(x['status']=='pass' for x in rs)}/{len(rs)} |")

text='''# Codex GPT-6.1 Sol: programming-language evaluation

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

'''+ '\n'.join(table)+'''

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

'''+ '\n'.join(runtime_table)+'''

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

'''+ '\n'.join(f'- {names[l]}: {versions[l]}' for l in names)+'\n\nAccuracy: 88% | Evidence: strong | Main uncertainty: small workload sample and future support\n'
(ROOT/'Evaluation_Report.md').write_text(text)
print(ROOT/'Evaluation_Report.md')
