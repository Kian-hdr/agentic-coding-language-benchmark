# Preregistered deeper comparison

Priorities: correctness/reliability, CPU and memory efficiency, platform/device
compatibility and long-term support; model effort/cost remains a separate metric.

Nine original languages. Same GPT-6.1 Sol medium Codex CLI configuration as pilot.
One new multi-operation application per language, not an independent-language
statistical sample. Three stages: initial implementation (720 s), equal-budget
repair/optimization (360 s), and maintenance request (240 s). Preserve source,
artifacts, logs and CPU results per stage. No edits to existing products.
No silent manual business-logic fixes. Failed programs do not receive speed credit.

Realistic workloads: transaction reconciliation, access-log latency aggregation,
and rolling telemetry analytics in a long-lived file worker. One process handles
all NDJSON requests; this tests sustained component/batch processing, NOT HTTP,
TLS, native UI, mobile battery usage or real-device compatibility.

Datasets have small/medium/large scales and varied independent contents. Correctness
adds malformed JSON recovery, mixed operations, request isolation, 32-bit overflow
boundaries, differing identifier lengths, CRLF and final-line handling. Holdout
cases are separate from cases disclosed in optimization feedback.

Builds are release/optimized, excluded from runtime measurements. Timings use one
worker at a time in randomized blocks, prewarmed dataset filesystem cache, same
machine and environment. Capture elapsed time, per-child user+system CPU from
wait4, and peak RSS (Darwin bytes, Linux KiB converted). Report CPU seconds per
million input events/samples and correct output; record input/output bytes too.
Five repetitions for medium/large sustained workloads, startup/empty baselines
separately. Set common numerical-library thread counts to one; record runtime
configuration. Do not alter OS security, power modes or unrelated workloads.

Output-file transport avoids pipe deadlocks and shell argument limits. Timeout
30 seconds per workload run, terminate only its process group. After two runtime
timeouts for a language/stage, stop remaining performance cases for that language
as explicitly unmeasured, not proven failures. Peak RSS and CPU
refer to direct prebuilt workers; no subprocess-per-record implementations.
Warm per-request p95/p99 and energy are NOT inferred from bulk elapsed time.
Memory scaling is measured across input sizes; lack of growth in this bounded
sample is not proof of no leak. Report actual measurements/variability.

Final follow-up: after maintenance, run an additional 8x-large batch per kind
in a single process, two randomized repetitions, 120-second cap and the same
two-timeout safeguard. Transform records between repeated blocks and recompute
oracles so full request caching cannot trivially replace computation. This
longer pass reduces (but does not remove) startup/JIT influence. Only final
correct/reproducibly buildable implementations are resource-ranked. Skipped
ineligible candidates remain reported. Preserve output hashes and discard only
verified task-created successful output payloads to keep disk use bounded.

Measure optimization gains against the same baseline code/workload and report
correctness before speed. Agent usage includes cached/uncached inputs, output,
failed commands and elapsed time; do not invent dollar prices. Maintainability
means a specified backwards-compatible fee feature plus original regression tests.

Compatibility is a per-use-case hard gate. Distinguish documented OS/architecture,
framework and distribution paths from actual clean-device tests. Local runtime
results are Apple Silicon macOS only. Public Windows/Linux/mobile/browser tiers
must explicitly identify the research-only compatibility evidence.

No universal weighted score. Publish per-use-case tiers, Pareto tradeoffs and
production eligibility. Any cross-platform or full-service claims untested here
remain explicit gaps. Native-library Python optimization is disclosed separately
from the pure-language baseline, with dependencies/packaging consequences.

## User clarification after measurements, October 27, 2026

Compatibility is a lower-weight practical check for current flagship devices
relevant to the intended product. Do not reward compatibility with extremely old
devices or treat legacy OS reach as a dominant KPI. Correctness, compute use,
continued support and agent effort retain priority. Preserve the original test
protocol/results; this clarification changes the final adoption rubric only.
