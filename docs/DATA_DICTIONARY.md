# Data dictionary and provenance

Paths below are repository-relative. Language identifiers are `python`, `typescript`, `go`, `rust`, `swift`, `kotlin`, `moonbit`, `baml`, `zero`. Human labels can differ, e.g. Zero is reported as Zerolang and TypeScript executes through Node.

## Layout and evidence types

| Route | Meaning |
|---|---|
| `archive/pilot/reports/` | Historical task plan, methods and interpretation; prose may contain local planning terminology or historical links |
| `archive/pilot/prompts/LANGUAGE_TRIAL/` | Published task prompts; not the full system/global instruction context |
| `archive/pilot/metrics/LANGUAGE_TRIAL/` | Per-turn authoring observations and provider-reported usage |
| `archive/pilot/sources/LANGUAGE_TRIAL_PHASE/` | Model-authored initial/extension source snapshots |
| `archive/pilot/results/` | External evaluations, prepared/delivered runtime probes, sorting probes and pilot summary |
| `archive/deep/reports/` | Historical local protocol, specification, deep report and derived summaries |
| `archive/deep/prompts/LANGUAGE/` | Initial, optimized and maintenance user prompts |
| `archive/deep/metrics/LANGUAGE/` | Timed model-turn status/counters; supplementary NumPy has a separate route |
| `archive/deep/sources/LANGUAGE/STAGE/source/` | Model-authored stage snapshot, build/worker wrappers and local tests/feedback where exported |
| `archive/deep/results/` | Historical builds, validations, standard perf, long-run and NumPy observations |
| `archive/deep/scripts/` | Historical runner, oracle and analysis/harness sources; not portable publication entry points |
| `archive/deep/compatibility/` | Metadata, cross-build/local-smoke evidence and preserved correction history |
| `archive/toolchain_notes/`, `archive/reviews/` | Dated research/setup and AI-assisted review; not independent replication |
| `data/index.json` | Frozen standard dataset metadata and intended stages |
| `data/frozen/*.jsonl.gz` | Compressed synthetic requests and oracle responses |
| `data/fixtures.json` | Compressed/uncompressed hash and byte-count manifest |
| `data/long_manifest.json` | Metadata/hashes for reconstructed longer inputs/expectations |
| `scripts/` | Later publication tooling; its runs are separate from historical observations |

## Turn metrics

Historical authoring metrics commonly contain:

| Field | Definition |
|---|---|
| `language`, `trial`, `phase` / `stage` | Identity; pilot phases are initial/extension, deep stages initial/optimized/maintenance |
| `model`, `reasoning` | Recorded selection alias/setting; not a cryptographic model-weights identifier |
| `seconds` | Wall time around the model process, including tools and waiting |
| `timed_out` | Runner deadline expired; separate from later source build correctness |
| `exit_code` | Model process status; not application correctness |
| `usage` | List of provider usage receipts; empty list means unavailable/unknown |
| `input_tokens` | Accumulated input as reported, including cached input |
| `cached_input_tokens` | Reported cached subset of input |
| `output_tokens` | Provider output counter |
| `reasoning_output_tokens` | Separate reported counter; do not automatically add it to output |
| `commands` / `tool_calls` | Historical runner's command/item count; counters can differ by harness |
| `failed_commands` | Nonzero shell commands, including lookups/tests/compiler errors; not a pure compiler-error rate |

Derived uncached input is `input_tokens - cached_input_tokens`. Decimal units: kTok = 10³, MTok = 10⁶. An absent receipt is never substituted with zero. Published metrics omit raw private event transcripts, so counter extraction can be inspected in code but not fully replayed from all events publicly.

## Dataset metadata

`name`, `kind`, `size`, `input`, `expected`, `expected_maintenance`, `items`, `requests`, `stages` identify a fixture. `items` means invoice/log events or telemetry samples, not bytes or requests. Validation sets can have zero aggregate items metadata and still contain requests. `requests` is expected nonblank response count. Empty files intentionally have zero.

Fixture manifest `gzip` gives compressed route; `compressed_sha256` hashes archive bytes, `sha256` hashes uncompressed bytes, `bytes` is uncompressed size. These are distinct. Long metadata additionally records `blocks`, source items/requests/hash, transformed input/expected bytes and hashes. Source files are not multiplied in place. Long-file creation regenerates oracle answers after deterministic transformations.

## Runtime records

| Field | Meaning |
|---|---|
| `language`, `dataset`, `kind`, `size`, `repetition`, `sequence` / `global_sequence` | Program/workload and scheduling identity |
| `command`, `input`, `expected`, `output_file`, `stdout_file`, `stderr_file` | Historical invocation/artifact routes; redacted markers are descriptive, not executable paths |
| `elapsed_seconds` | Measured wall time for worker lifetime |
| `user_cpu_seconds`, `system_cpu_seconds`, `cpu_seconds` | Child lifetime CPU; total is user + system |
| `peak_rss_raw`, `peak_rss_source_units` | OS-reported high-water mark and its original unit |
| `peak_rss_bytes`, `peak_rss_mib` | Converted bytes and bytes / 1,048,576 |
| `runtime_environment` | Declared threading environment; not proof every dependency obeyed it |
| `exit_code`, `timed_out`, `termination_signals`, `launch_error` | Execution outcome; all must be interpreted before comparing speed |
| `correct` | Oracle comparison passed; can be true despite unsupported resource accounting |
| `actual_responses`, `expected_responses`, `mismatches`, `mismatch_count`, `checker_error` | Strict comparison evidence and errors |
| `valid` | Successful process completion plus correct output and no live remaining process-group members under historical harness rules |
| `resource_accounting_supported` | Additional resource comparability gate; observed descendants make direct-child accounting unsupported |
| `observed_descendant_pids`, `remaining_process_group_members` | Best-effort process snapshots; may be omitted/redacted for privacy, not exhaustive tracing |
| `measured`, `skipped`, `reason`, `correctness_established` | Whether execution was attempted; a skip is not an observed incorrect output |
| `input_bytes`, `expected_bytes`, `output_bytes`, `stdout_bytes`, `stderr_bytes` | File sizes; output/log content need not all be retained publicly |
| `output_sha256`, `output_deleted_after_comparison` | Hash before deletion of a correct task-created output; deletion does not mean missing correctness evidence |
| `cpu_seconds_per_million_input_items` | `cpu_seconds × 1,000,000 / items`, for valid supported records only |
| `input_items_per_second` | Item count / elapsed time for valid output; not HTTP request throughput |

No resource credit is inferred from `correct` alone. The two final long exclusions are BAML/invoice/repetition 1 and Kotlin/telemetry/repetition 0. Their task output is correct; CPU/RSS summaries use only the other repetition and label n=1.

## Reports and summaries

Standard `*_STAGE_build.json` stores build exit/time and diagnostic excerpts. `*_STAGE_validate.json` and `*_STAGE_perf.json` store `records` plus summaries (`planned`, `attempted`, `valid`, `skipped`, `pending`, `all_valid`). A validation valid count usually counts **files**, not request cases. Final four files contain 221 responses. Standard perf has 33 records per language/stage.

`long_run.json` also contains eligibility reasons, randomized `schedule`, dataset metadata and status. It reports 54 scheduled records, including ineligible skips. Its summary's 48 valid records include two resource-unsupported correct records; supported resource count is 46.

Historical `archive/deep/reports/Summary.json` aggregates supported medians/minima/maxima by language/workload, stage validations, model counters and NumPy results. Pilot `summary.json` aggregates two starts and four model turns per language. Historical source hashes may hash pre-redaction files. The public release's manifest, where supplied, verifies transformed archive bytes; do not confuse the two provenance layers.

## Redaction and reruns

Markers such as `{ORIGINAL_BENCHMARK_ROOT}` identify removed host paths. Public path changes preserve numerical measurements but alter file bytes. Raw private context and transcripts are omitted; this package is not a bit-for-bit mirror of the private experiment. Record all publication transformations and preserve the original local evidence privately. New software reruns should have separate output destinations, actual toolchain/platform details and fresh timestamps, without rewriting historical result JSON.
