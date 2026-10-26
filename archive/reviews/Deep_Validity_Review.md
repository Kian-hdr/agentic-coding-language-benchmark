# Deep-phase measurement validity review

Read-only review, 26 October 2026. Reviewed the protocol, measurement/orchestration/agent runner code, archived and current worker/build scripts, completed initial/optimized results, and a maintenance snapshot while its performance run was still pending. No business source was edited and no benchmark was rerun. This reviewer previously authored the measurement harness; this is a fresh consistency audit, not a second-author independent verification of that harness.

## Conclusion

**No material CPU-unit, RSS-unit, direct-execution or output-alignment defect was found in the completed initial and optimized comparisons.** They support comparisons of these particular startup-inclusive, prebuilt, macOS ARM64 bulk workers on the recorded workloads. They do not establish universal language speed, production eligibility, steady-state server throughput, per-request tail latency or energy consumption.

There are two material reporting requirements: missing token usage on timed-out model phases must remain unknown/incomplete, and candidate-level resource rankings must exclude implementations that fail required correctness/build gates even when selected individual workload records happen to pass.

## Measurement checks

- Per-PID `os.wait4` owns process reaping; Popen's returncode is assigned afterward. User and system CPU are recorded in seconds and summed, rather than inferred from wall time or global children deltas. The observer's own `ps` processes are outside the worker's new process group and are not mistaken for application CPU. Their small scheduling overhead remains environmental noise, especially for tiny jobs.
- Darwin raw RSS is treated as bytes, then divided by 1,048,576 for MiB. Every observed completed initial/optimized record reports bytes. Checked internal arithmetic: CPU=sum(user,system), RSS_bytes=raw, and RSS_MiB*1,048,576=raw. No conversion inconsistency found.
- All 27 archived stage worker scripts plus current wrappers use `exec` into prebuilt native/runtime artifacts. No build command was found in those wrappers. Kotlin executes Java with a precompiled JAR; Python executes prepared bytecode; TypeScript executes precompiled JS; BAML executes its packed worker. Shell argument/path resolution is setup overhead, not per-record computation. Zero maps stdout into the required output file through shell redirection, which is transport rather than an algorithm.
- Completed initial/optimized records report no observed extra application-group PIDs. The source wrappers support the intended direct-process interpretation. Snapshot observation cannot prove no extremely short-lived subprocess ever exists, but no evidence invalidating direct-worker RSS/CPU comparisons was found. Peak RSS remains lifecycle high-water memory, not aggregate process-tree memory or a leak test.
- The timeout watchdog targets only the worker's created process group. Output, stdout and stderr use separate files; they cannot fill an undrained pipe. Missing/extra/malformed responses and nonzero exits fail eligibility. No pipe-deadlock artifact was found.
- The worker-lifetime wall interval includes spawn/startup and shutdown (and tiny parent file-open setup). CPU/RSS also include runtime startup, GC/JIT and shutdown. Builds, dataset prewarming and output validation are outside measured worker execution. Therefore short-job CPU/memory results are not steady-state measurements. The planned longer 8x-large pass reduces startup/JVM influence but does not remove it; its existing report limitations correctly say so.

## Correctness and record alignment

The checker compares nonblank response records in order with a separate expected-output file. It checks response counts, recursively rejects boolean/numeric equivalence, accepts numerically equal integral JSON values such as 1 and 1.0, and rejects nonfinite numbers and duplicate object keys. That agrees with the chosen numeric-response policy. Skipping blank lines is consistent with the input-line protocol and does not shift a nonblank response onto another expected record.

For both completed stages, every language has exactly 33 scheduled records. Global sequences uniquely cover 0 through 296 across all nine languages; there are no duplicated or missing ordinals. Each stage has one shared seed and records the all-language/dataset-block randomization scope. Repetition counts are five per medium/large dataset plus three empty baselines per language. Languages are interleaved within blocks, rather than measured as one whole language then another. Per-language reports preserve global ordinals and independent failure/skip handling.

Eight candidates passed all 33 performance records in both stages and their separate mandatory validation reports. Zero passed no performance record in those stages and its rebuilds failed; no normalized CPU values were assigned to its failed records. Thus stale/missing Zero artifacts did not accidentally receive performance credit. Across completed stages, every normalized CPU-per-million field was guarded by valid correctness plus supported resource accounting.

**Do not promote per-dataset validity to whole-candidate eligibility.** In the maintenance snapshot Zero passes some workload records but fails its complete validation suite (2/4 validation files pass). Its valid per-operation CPU numbers can remain evidence, but it must not be ranked as a fully correct candidate. `long_run.py` correctly gates on a successful final maintenance build and every mandatory final validation record before resource ranking. Retain that gate in the final report. Skipped timeout-budget cases are unmeasured, not proof their answers would be wrong.

The separate oracle review found no blocker in invoice deduplication, log p95, signed averages or optional-fee semantics. This audit did not broaden or rerun those algorithm tests.

## Model usage and sample limits

`deep_phase/agent_runs.py` appends provider usage only when emitted in the raw events. Optimized MoonBit, Zero, Rust and Kotlin phases have `timed_out=true` and `usage=[]` in the inspected metrics. They certainly consumed model work; absence of a completed usage event does **not** mean zero input/output tokens. Report phase usage as unknown or incomplete. If presenting a total from only reported phases, label it a lower bound and exclude it from claims of lowest complete token cost. The authoring wall budget and observed completed command counts remain usable, with in-flight work noted as incomplete.

One application implementation per language, refined over three stages, is not multiple independent authoring samples. Five runtime repetitions reduce execution noise; they do not turn one generated program into five independent tests of the language/model pairing. Optimization gains describe the same implementation after additional model effort. Maintenance success describes the specified optional-fee change and regression suite, not general maintainability.

## Support and compatibility boundaries

The inspected protocol and compatibility research separate local runtime evidence from documented platforms and deployment research. Preserve those distinctions: cross-compilation, target-list presence, Wasm output or a framework bridge is not clean-device installation, native UI parity or validated Windows/Linux/mobile behavior. Current measurements are macOS Apple Silicon only. JVM deployment/runtime packaging and Apple-only frameworks are distinct from core language portability.

Governance, maintainers, license, release cadence and platform ownership are continuity proxies. They can justify relative migration caution, but not a numerical probability of survival or a guarantee of ongoing support. In particular, a Vercel Labs experimental repository is not a commercial support commitment. No new external support claims were inferred in this review.

## Final-report conditions

1. Use globally correct, reproducibly buildable final implementations for overall CPU/RSS comparisons; retain failed/skipped candidates as visible outcomes.
2. Label all recorded runtime/resource numbers startup-inclusive bulk-worker measurements. Do not infer p95/p99 request latency, power use or pure algorithm speed.
3. Keep timed-out usage unknown/incomplete and distinguish complete token totals from lower bounds.
4. Finish maintenance and the queued longer pass before describing them as completed; report partial records as pending until then.
5. Keep documentation-only compatibility and maintenance-risk inferences separate from actual local tests.

Within these conditions, no finding from this bounded review requires discarding the completed initial/optimized CPU/RSS measurements.

## Final-phase extension, 27 October 2026

The maintenance, final long-run and NumPy-reference results are now complete. This extension remains read-only and does not rerun workers. The earlier maintenance-pending statements describe the earlier snapshot, not the current completion state.

### Final eligibility and exact counts

- Eight original candidates finish with 4/4 mandatory validation files passing and 33/33 maintenance performance records correct. Zero finishes with 2/4 validation files passing; its maintenance performance has 28 correct of 29 attempted records plus four explicitly skipped repeats. Selected passing operations therefore do not restore its whole-candidate eligibility.
- `long_run.json` is complete: 54 scheduled/recorded records, 48 measured/correct, six skipped, zero timeouts and zero pending. The six skips are exactly Zero's three workload kinds times two repetitions, because final validation is incomplete. This is an eligibility exclusion, not six measured failures.
- Every measured long-run record has exactly 4,096 expected and actual responses. That is 196,608 correctly compared responses across 48 measured runs. Each invoice/access-log run processes 2,097,152 input events; each telemetry run processes 16,777,216 samples. Record `(language,kind,repetition)` triples are unique, and sequence values cover 0 through 53 exactly. Final build/validation hashes recorded by the eligibility gate still match their source reports.
- No unsupported process-tree resource rows were found in any initial, optimized or maintenance per-language perf report.

### Two long-run resource records must remain excluded

Two correct-output records explicitly have `resource_accounting_supported=false` and `process_tree_unsupported=true`:

| Record | Observed additional group PIDs | Consequence |
|---|---|---|
| Kotlin telemetry, repetition 0 | 95134, 95153 | Keep correctness evidence; exclude this CPU/RSS cell from direct-worker resource ranking |
| BAML invoice, repetition 1 | 97014, 97015 | Keep correctness evidence; exclude this CPU/RSS cell from direct-worker resource ranking |

Their normalized CPU-per-million fields are correctly absent. A downstream report must not recreate those missing fields by normalizing raw `cpu_seconds`, or silently include their RSS while filtering only CPU. Each affected workload/language cell has only **one supported resource repetition** remaining. The source wrappers still exec the intended runtime, but PID-only snapshots cannot now establish whether those extra processes were transient launch helpers or runtime children; do not erase the flags based on a guess. The parent acknowledged this reporting gate.

### Variation and the two-repetition limit

There are only two final repetitions, and sometimes substantial variation. These are observed ranges, not confidence intervals:

- TypeScript CPU ranges are tight: invoice 0.536–0.551 s, access-log 0.501–0.512 s, telemetry 0.326–0.329 s.
- Rust invoice CPU is 0.638–0.741 s while wall time is 0.746–1.428 s; access-log CPU is 0.561–0.562 s; telemetry CPU is 0.376–0.398 s.
- MoonBit access-log CPU changes from 1.218 to 2.345 s and wall time from 1.247 to 6.182 s, despite both outputs being correct and resource records supported.
- Kotlin invoice CPU is 1.700–2.354 s and wall time 1.211–2.852 s. BAML access-log CPU is 5.997–6.730 s and wall time 7.326–8.542 s. The flagged BAML/Kotlin records above must not supply additional supported ranges.

These differences are not explainable as a single fixed startup subtraction. Scheduling, filesystem/runtime behavior and JIT/GC may contribute, but were not individually profiled. Do not assign a definite cause. CPU is generally less directly affected by waiting than wall time, but the observed CPU variation also prevents treating tiny ranking gaps as stable language properties. Two repetitions cannot establish p95/p99, a narrow confidence interval or a steady-state asymptote. The longer pass remains startup-inclusive and uses one authored implementation per language.

### Why TypeScript beating this Rust worker is plausible

Read the current TypeScript `application.ts`/`worker.ts` and Rust `src/main.rs`/`src/fast.rs`. No cross-request response cache, hardcoded dataset answers, benchmark seed in business logic or fixture-size-dependent answer shortcut was found in those implementations.

TypeScript uses ordinary `JSON.parse`, per-request Set/Map aggregation, a linear rolling-window loop, three-way p95 selection with a bounded-work fallback to sorting, and a BigInt fallback when numeric accumulations cease to be safe integers. This is actual computation on each request. Rust uses serde-derived typed envelopes with borrowed `RawValue`, a second visitor pass over event/sample bodies, borrowed-or-owned decoded strings, BTreeMap ordering, and `select_nth_unstable`. Its parsing path can inspect the same body during envelope validation and again while extracting typed values. Its numeric/ownership choices and memory economy are different from TypeScript's native JSON parser plus JIT-optimized arrays/maps.

Both implementations use general algorithms consistent with the specified schemas. The result is an observed implementation/runtime tradeoff, not evidence that TypeScript inherently outruns optimized Rust. A CPU profile or independently optimized second Rust implementation would be needed to attribute the gap. Those were not performed here. Rust's substantially smaller recorded RSS is a separate result and should remain visible beside CPU.

The other inspected optimizations also use ordinary implementation strategies: Go reuses typed request/event buffers and resets request state; Swift and Kotlin use handwritten typed JSON scanners instead of generic object trees; BAML parses then converts to typed request classes; MoonBit uses its JSON APIs. Custom scanners expand the correctness surface. Inspection and the frozen validations do not prove equivalence for all possible JSON/schema extensions, but no benchmark-specific cache or semantic answer shortcut was identified in the reviewed paths. Their exact integer ranges, malformed-input handling and supported schemas must remain the claim boundary. Passing current tests is not a general parser certification.

### NumPy reference

The reference is correctly labeled **exploratory extra-prompt**, with a new NumPy dependency and runtime environment, rather than another equal-budget language result. Its build and all four final validation files pass; all six long-file records (three kinds times two repetitions) are correct, each comparing 4,096 responses, and all six have supported resource accounting with no observed extra group processes.

The source change replaces the telemetry kernel with NumPy int64 array arithmetic: rolling-sum differences, cumulative sums, absolute integer division followed by sign restoration, threshold counting and a weighted dot product. It avoids floating-point division. Within the stipulated safe-integer bounds, the difference/cumulative-sum construction stays well inside signed int64 and the sign restoration implements truncation toward zero. The window-one shortcut computes directly on the samples and is semantically valid. Invoice and log task logic remain unchanged; NumPy import/startup still adds overhead/memory to their runs.

The reference's six runs were executed afterward in sequential workload/repetition order, not interleaved with the nine-language long-run blocks. Thus a direct causal speedup estimate is weaker than a paired randomized same-window comparison. It can illustrate the opportunity from a native numerical library, with its dependency/import/memory consequences, but should not be used to claim a statistically established language-wide speedup or lower agent token cost. The additional prompt effort is separate and disclosed.

**Final audit disposition:** retain the completed correctness evidence. Retain supported CPU/RSS records with explicit sample counts and ranges. Exclude the two flagged resource cells, retain Zero's ineligible status for overall resource rankings, and keep NumPy outside the equal-budget main comparison. No business edits or performance reruns were made by this review.
