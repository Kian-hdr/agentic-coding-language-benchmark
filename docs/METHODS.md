# Methods

## Status and experimental question

Independent descriptive research by Kian-hdr, with AI assistance in research, implementation orchestration, analysis and review. The experiment asks how usable nine languages are when an agent writes bounded deterministic software and later changes it. It does not estimate a population-wide average language effect.

Experiments ran October 26–27, 2026 on one Apple Silicon macOS host. The retained [protocol](../archive/deep/reports/PROTOCOL.md) and [pilot task plan](../archive/pilot/reports/BENCHMARK.md) are local planning artifacts. Their use of “preregistered” denotes a local plan, **not an externally timestamped preregistration**. The scope expanded during the investigation. The longer final pass and NumPy supplement were later exploratory follow-ups. Analysis and public packaging were added after measurement.

## Experimental units and counts

Nine languages were tested: Python, TypeScript, Go, Rust, Swift, Kotlin, MoonBit, BAML and Zerolang. All timed authoring used the recorded Codex alias `gpt-6.1-sol`, medium reasoning. The model service/backend is proprietary, may change, and may not be accessible under that alias to another reader.

The pilot has two fresh implementation starts per language. Each start contains an initial turn and a later feature-addition turn: 9 × 2 × 2 = 36 main model turns. The deeper experiment has one new application per language, with three turns: 9 × 3 = 27 main turns. Total: 63 main turns, plus one extra-budget NumPy turn. Runtime repetitions reuse the same generated source; they are not independent authoring samples. Repair and maintenance turns continue a codebase and are not new applications.

## Authoring controls and remaining confounders

The historical runner selected the model and reasoning setting, requested ephemeral sessions, ignored user configuration, disabled named apps/plugins/memory/multi-agent mechanisms, and requested workspace-limited terminal work. These flags describe intent; they do not establish that every hidden/global instruction or tool context was absent. Prompts prohibited network/package installation during timed turns, other-language business computation, evaluator/other-run access, delegation and public deployment. Language-specific setup and approved dependencies were staged beforehand.

The agent could read its task, a language packet, toolchain help/standard-library source and its own code/tests; compile, execute, inspect failures and repair within budget. Packets differed in size and discovery burden. Some authoring ran concurrently, so time includes model-service latency, tool waiting and host contention. The local environment and unavailable system context cannot be made exactly identical for a future proprietary model run. Scope/log review found no obvious answer-copying or outsourced business logic, but this was not adversarial sandbox certification. Public transcripts are omitted, so readers cannot repeat every trace-level check from the public package alone.

## Pilot

The [specification](../archive/pilot/reports/BENCHMARK.md) defines ledger deduplication/grouping, lexically ordered topological sort and integer expression evaluation. Later, interval merging must be added without regressions. Interfaces use a request filename and one JSON response. Integer semantics, ordering and error precedence are specified; successful arithmetic fits signed 32-bit bounds.

Initial cap: 480 seconds. Extension cap: 240 seconds. Two fresh starts per language. External checks contain 69 initial cases and 89 extension cases; the latter repeat the original 69. Thus 316 observations per language are repeated checks, not 316 independent tasks. Larger workloads, sorting and compiler-validation probes were added to distinguish limitations obscured by initial pass rates. Process timings and prepared-executable timings are separate; wrappers, compilation checks and argument/file transport can differ.

## Deeper task and maintenance

[Deep specification](../archive/deep/reports/SPEC.md): one process reads a JSONL file incrementally and writes one response per nonblank request line, preserving order. Operations are invoice reconciliation/deduplication, access-log aggregation with exact nearest-rank p95, and integer rolling telemetry. The worker must recover from malformed JSON and isolate independent requests.

Turn budgets: 720 seconds initial, 360 seconds repair/optimization, 240 seconds maintenance. Initial feedback contains observed failures and resource data. Maintenance adds optional `fee_bps`, computed per accepted paid event using the specified integer-rounding formula. Omitting the option must preserve the old schema; present zero must include zero-valued fee fields. Successful integer intermediates remain in the specified safe 53-bit domain. This deliberately does not test every language's full integer range.

Approved support includes JSON libraries for Rust/Kotlin and official native IO for MoonBit. All application computation remains in the target language. Python could use a staged NumPy environment during optimization, but the main implementation retained standard-library computation. A later separate prompt produced the supplementary NumPy kernel. Dependency use and runtime paths are part of the evaluated implementation, not pure-language compiler comparisons.

## Fixtures and oracle

All data are synthetic. Standard workloads have 8, 64 and 512 requests at small/medium/large scales. Invoice/log requests have 512 events; telemetry requests have 4,096 samples. The initial/optimized validation sets include malformed data, ordering, recovery, line-format and numeric cases. Final validation has four files: 80 base cases, 12 formatting cases, 126 fee cases and three numeric holdouts, totaling 221 responses. Frozen fixture bytes and manifests are the authoritative released cases; inspect scripts and change history before assuming an older generation script produces every later-added holdout unchanged.

An external Python [oracle](../archive/deep/scripts/oracle.py) computes expected JSON. Strict comparison distinguishes booleans from numbers, rejects duplicate JSON object keys/nonfinite numbers, ignores JSON key ordering and compares expected response counts. Passing finite tests is not proof of semantic completeness. Schema-valid task inputs and invalid-JSON recovery tests are distinct; no general untrusted-input security claim follows.

The final long pass streams each large source eight times with transformations: prefix invoice IDs per block while preserving within-request duplicates; shift log timestamps and query boundaries equally by block × 100,000; add block × 13 to telemetry samples and recompute oracle outputs. Each resulting file has 4,096 requests; item counts increase eightfold. This avoids identical full-request reuse across blocks but does not rule out every possible shortcut or constitute a cache-adversarial proof.

## Measurement

Compilation/release packaging occurs before worker timing. Measurements are sequential, with randomized language/workload order in recorded blocks, warmed input-file cache and declared single-thread numerical-library environment variables. The original host was not reserved as a dedicated laboratory machine. No power-mode or unrelated-workload control is implied.

Historical `measure.py` uses a child process group, a timeout watchdog and `wait4` for user/system CPU and maximum RSS. CPU is user plus system seconds. Darwin RSS is bytes; Linux reports KiB and would require conversion. Wall/CPU/RSS include worker startup, parsing, application computation, output IO and shutdown. Oracle generation and output comparison occur outside the timed worker lifetime. Peak RSS is the direct-child lifetime maximum, **not summed tree RSS**, private heap or billable container memory. Independent wrapper review is needed because process snapshots can miss short-lived descendants.

Each standard stage schedules 297 records: 9 languages × (six medium/large workloads × five repetitions + three empty baselines). Standard timeout is 30 seconds. After two language/stage runtime timeouts, remaining perf cases are explicit budget skips rather than proven failures. A dataset failure can stop repeated samples of that dataset; this is recorded.

The final long pass requires all stages complete and final maintenance build/validation success. It schedules two randomized repetitions of three workloads per language: 54 records. Ineligible languages remain in the schedule as explicit skips. Timeout is 120 seconds; two timeouts stop further work for that language. Correct outputs are hashed and their byte counts saved before task-created output files may be removed to control disk use. Failure diagnostics remain in the private evidence; the public package preserves selected records and excerpts subject to privacy filtering.

## Analysis and exclusions

Correctness and process completion precede speed credit. Resource summaries further require `resource_accounting_supported`. BAML invoice repetition 1 and Kotlin telemetry repetition 0 are correct but resource-unsupported because extra process-group members were observed; exclude their CPU/RSS, retain correctness and label the remaining cell n=1. Two repetitions have no credible narrow confidence interval. No inferential significance test, overall weighted score or causal “language winner” is claimed.

CPU per million input items is `cpu_seconds × 1,000,000 / items`, only for correct resource-supported records. Invoice/log events and telemetry samples are different units; do not pool them into a cross-workload score. Token units are decimal; uncached input is reported input minus cached input. Cached tokens remain input/cost. Missing receipts are unknown, not zero, and reasoning output is not blindly added again to provider output.

## Interpretation priorities

The original practical decision prioritized correctness/reliability, compute/memory and continued support. Development effort was separate. The final clarified compatibility brief concerns relevant current flagship devices and operating systems, with lower decision weight and no reward for obsolete hardware. Compatibility remains a requirement for a promised target, not a universal score. UI/framework fit and institutional support are qualitative research, not measured outcomes of these CLI tasks.

This publication does not authorize a product migration. It offers source, fixtures and observations with boundaries. Independent fresh implementations, more tasks/models, repeated controlled measurement and actual product/device tests are needed before a broad adoption claim.
