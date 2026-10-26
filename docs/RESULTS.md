# Results

These are descriptive observations from the October 26–27, 2026 experiment. Source: archived raw JSON, with the retained Summary used as a cross-check. Runtime repetitions reuse generated programs; they do not estimate agent reliability across independent projects. See [methods](METHODS.md) and [limitations](LIMITATIONS.md).

## Final longer workers

CPU seconds are whole-process user + system time. Values are supported medians, n=2 unless n=1 is shown. Correctness, successful completion and supported resource accounting are all required for CPU/RSS credit. Resource-supported RSS is a process lifetime high-water mark, not a native heap or desktop-app footprint.

| Language/runtime | Invoice CPU s | Log CPU s | Telemetry CPU s | RSS range MiB |
|---|---|---|---|---|
| Python | 1.064 | 1.366 | 2.383 | 14.4–15.1 |
| TypeScript / Node | 0.544 | 0.507 | 0.327 | 65.2–83.6 |
| Go | 1.051 | 1.045 | 0.622 | 5.5–12.1 |
| Rust | 0.689 | 0.561 | 0.387 | 2.2–2.6 |
| Swift | 1.711 | 1.633 | 0.548 | 9.1–9.6 |
| Kotlin / JVM | 2.027 | 1.727 | 1.022 (n=1) | 184.3–312.6 |
| MoonBit native | 1.202 | 1.781 | 0.648 | 3.6–4.4 |
| BAML | 5.313 (n=1) | 6.363 | 2.088 | 86.3–100.8 |
| Zerolang | Ineligible | Ineligible | Ineligible | — |

TypeScript/Node has the lowest supported median CPU in each of these three generated workers. Rust has the lowest RSS. These results compare actual generated algorithms, parsing/allocation strategies and runtimes on this host. They do not identify an intrinsic language limit. In particular, a JVM CLI worker's RSS is not an Android app's memory measurement; a Node worker is not an Electron app.

The final schedule has 54 records: 48 correct executions and six Zerolang eligibility skips. No final long case timed out. Two correct executions had unsupported process-tree accounting: BAML invoice repetition 1 and Kotlin telemetry repetition 0. Their performance values are excluded, leaving 46 supported resource observations; the other repetition supplies the n=1 cell. All eight eligible languages passed final validation; Zerolang's final build succeeded but validation remained incomplete.

| Workload | Requests | Input events/samples | Input bytes | Expected bytes |
|---|---|---|---|---|
| invoice | 4,096 | 2,097,152 | 164,301,240 | 11,966,992 |
| access_log | 4,096 | 2,097,152 | 179,363,491 | 13,749,936 |
| telemetry | 4,096 | 16,777,216 | 107,426,662 | 345,169 |

### Individual supported observations

| Language | Workload | CPU s, recorded order | RSS MiB, same order |
|---|---|---|---|
| Python | invoice | 1.1099, 1.0178 | 15.0, 15.0 |
| Python | access_log | 1.4035, 1.3279 | 15.1, 15.1 |
| Python | telemetry | 2.4099, 2.3556 | 14.8, 14.4 |
| TypeScript / Node | invoice | 0.5510, 0.5364 | 83.2, 82.9 |
| TypeScript / Node | access_log | 0.5123, 0.5010 | 83.6, 83.2 |
| TypeScript / Node | telemetry | 0.3292, 0.3258 | 65.4, 65.2 |
| Go | invoice | 1.1047, 0.9975 | 11.6, 12.0 |
| Go | access_log | 1.0986, 0.9923 | 11.2, 12.1 |
| Go | telemetry | 0.6800, 0.5633 | 5.5, 6.0 |
| Rust | invoice | 0.6377, 0.7410 | 2.6, 2.6 |
| Rust | access_log | 0.5609, 0.5616 | 2.4, 2.4 |
| Rust | telemetry | 0.3757, 0.3979 | 2.2, 2.2 |
| Swift | invoice | 1.9046, 1.5165 | 9.5, 9.6 |
| Swift | access_log | 1.5766, 1.6902 | 9.5, 9.6 |
| Swift | telemetry | 0.5888, 0.5075 | 9.1, 9.1 |
| Kotlin / JVM | invoice | 1.6996, 2.3537 | 292.9, 307.1 |
| Kotlin / JVM | access_log | 1.6674, 1.7862 | 312.6, 297.0 |
| Kotlin / JVM | telemetry | 1.0217 | 184.3 |
| MoonBit native | invoice | 1.1711, 1.2324 | 4.2, 4.3 |
| MoonBit native | access_log | 1.2177, 2.3451 | 4.4, 4.3 |
| MoonBit native | telemetry | 0.6203, 0.6758 | 3.7, 3.6 |
| BAML | invoice | 5.3132 | 88.5 |
| BAML | access_log | 5.9968, 6.7296 | 95.1, 100.8 |
| BAML | telemetry | 2.0538, 2.1227 | 86.4, 86.3 |

Two observations do not support tight confidence intervals. MoonBit log CPU, for example, ranges from about 1.218 to 2.345 seconds; scheduling, IO and runtime contributors were not separately profiled. Longer files reduce the relative impact of startup but do not establish indefinitely warm JIT steady state. [Raw final records](../archive/deep/results/long_run.json).

## Standard deep stages

These tables cover the **large** standard workload only, with five repetitions where successful. They are shorter batches than the final 8× workloads; do not compare their raw seconds without accounting for scale. Each stage schedules 33 performance records per language (six medium/large datasets × five repetitions, plus three empty baselines), 297 overall. Eight non-Zero languages pass all 33 at every stage. Resource support is separate from functional validity.

### Initial

| Language | Build exit | Validation files pass | Perf records valid | Invoice CPU s | Log CPU s | Telemetry CPU s | RSS MiB range |
|---|---|---|---|---|---|---|---|
| Python | 0 | 2/2 | 33/33 | 0.1426 (n=5) | 0.1898 (n=5) | 0.2642 (n=5) | 14.4–15.0 |
| TypeScript / Node | 0 | 2/2 | 33/33 | 0.1255 (n=5) | 0.1345 (n=5) | 0.1221 (n=5) | 59.7–69.5 |
| Go | 0 | 2/2 | 33/33 | 0.1445 (n=5) | 0.1647 (n=5) | 0.1424 (n=5) | 10.7–12.0 |
| Rust | 0 | 2/2 | 33/33 | 0.1005 (n=5) | 0.1021 (n=5) | 0.0430 (n=5) | 2.5–2.9 |
| Swift | 0 | 2/2 | 33/33 | 0.3671 (n=5) | 0.5374 (n=5) | 0.2554 (n=5) | 47.7–68.5 |
| Kotlin / JVM | 0 | 2/2 | 33/33 | 0.7912 (n=5) | 1.0488 (n=5) | 0.9489 (n=5) | 294.2–312.1 |
| MoonBit native | 0 | 2/2 | 33/33 | 0.1541 (n=5) | 0.1570 (n=5) | 0.0808 (n=5) | 3.6–4.3 |
| BAML | 0 | 2/2 | 33/33 | 0.9333 (n=5) | 2.3158 (n=5) | 0.2932 (n=5) | 77.7–88.2 |
| Zerolang | 1 | 0/2 | 0/33 | No supported result | No supported result | No supported result | — |

### Optimized

| Language | Build exit | Validation files pass | Perf records valid | Invoice CPU s | Log CPU s | Telemetry CPU s | RSS MiB range |
|---|---|---|---|---|---|---|---|
| Python | 0 | 2/2 | 33/33 | 0.1356 (n=5) | 0.1878 (n=5) | 0.2434 (n=5) | 14.4–15.0 |
| TypeScript / Node | 0 | 2/2 | 33/33 | 0.1121 (n=5) | 0.1140 (n=5) | 0.0860 (n=5) | 56.4–59.1 |
| Go | 0 | 2/2 | 33/33 | 0.1145 (n=5) | 0.1253 (n=5) | 0.0738 (n=5) | 5.4–11.4 |
| Rust | 0 | 2/2 | 33/33 | 0.0628 (n=5) | 0.0666 (n=5) | 0.0465 (n=5) | 2.2–2.5 |
| Swift | 0 | 2/2 | 33/33 | 0.1728 (n=5) | 0.1935 (n=5) | 0.0619 (n=5) | 8.6–9.4 |
| Kotlin / JVM | 0 | 2/2 | 33/33 | 0.5334 (n=5) | 0.6473 (n=5) | 0.3217 (n=5) | 79.8–216.8 |
| MoonBit native | 0 | 2/2 | 33/33 | 0.1412 (n=5) | 0.1549 (n=5) | 0.0804 (n=5) | 3.6–4.3 |
| BAML | 0 | 2/2 | 33/33 | 0.6239 (n=5) | 0.6569 (n=5) | 0.2885 (n=5) | 78.0–84.4 |
| Zerolang | 1 | 0/2 | 0/33 | No supported result | No supported result | No supported result | — |

### Maintenance

| Language | Build exit | Validation files pass | Perf records valid | Invoice CPU s | Log CPU s | Telemetry CPU s | RSS MiB range |
|---|---|---|---|---|---|---|---|
| Python | 0 | 4/4 | 33/33 | 0.1571 (n=5) | 0.1693 (n=5) | 0.2470 (n=5) | 14.7–15.0 |
| TypeScript / Node | 0 | 4/4 | 33/33 | 0.1162 (n=5) | 0.1188 (n=5) | 0.0857 (n=5) | 56.4–59.1 |
| Go | 0 | 4/4 | 33/33 | 0.1178 (n=5) | 0.1267 (n=5) | 0.0785 (n=5) | 5.4–11.2 |
| Rust | 0 | 4/4 | 33/33 | 0.0681 (n=5) | 0.0666 (n=5) | 0.0468 (n=5) | 2.2–2.5 |
| Swift | 0 | 4/4 | 33/33 | 0.1750 (n=5) | 0.1918 (n=5) | 0.0651 (n=5) | 8.7–9.4 |
| Kotlin / JVM | 0 | 4/4 | 33/33 | 0.5422 (n=5) | 0.6222 (n=5) | 0.3308 (n=5) | 73.8–219.0 |
| MoonBit native | 0 | 4/4 | 33/33 | 0.1460 (n=5) | 0.1592 (n=5) | 0.0811 (n=5) | 3.6–4.3 |
| BAML | 0 | 4/4 | 33/33 | 0.6410 (n=5) | 0.7313 (n=5) | 0.3058 (n=5) | 80.6–89.5 |
| Zerolang | 0 | 2/4 | 28/33 | 3.8274 (n=5) | No supported result | 1.1824 (n=5) | 11.9–12.1 |

Interpretation: implementation changes can matter substantially before changing languages. On the same standard large invoice input, Swift's median RSS fell from about 65.2 to 9.3 MiB between initial and optimized stages; BAML's log median CPU fell from about 2.316 to 0.657 seconds. These before/after observations are not randomized intervention effects. Timeouts of a model turn are also distinct from whether source left on disk builds and passes later checks.

Final maintenance validation consists of four files/221 expected responses: 80 base, 12 formatting, 126 fee and three numeric holdout cases. Eight languages pass all files. Zero passes two of four and fails long-customer-string cases in the base/formatting sets. Its initial/optimized builds had failed earlier. It remains in the records, but receives no final cross-language performance eligibility.

## Model authoring and maintenance effort

All values below are directly reported accumulated turn counters, not tokenized source lengths or dollar costs. Input accumulates repeated context during calls; uncached is input minus cached input. Decimal kTok = 1,000 tokens. Cached input remains a cost category. Reasoning counters are preserved separately because adding them blindly to output can double-count provider usage. Empty receipts mean unknown, not zero.

| Language | Turn | Elapsed s | Turn status | Uncached input kTok | Cached input kTok | Output kTok | Nonzero commands |
|---|---|---|---|---|---|---|---|
| Python | initial | 97.4 | Completed | 19.5 | 142.2 | 4.7 | 0 |
| Python | optimized | 217.9 | Completed | 46.1 | 697.5 | 7.6 | 1 |
| Python | maintenance | 45.4 | Completed | 30.0 | 158.0 | 2.2 | 1 |
| TypeScript / Node | initial | 160.0 | Completed | 30.6 | 235.3 | 6.8 | 1 |
| TypeScript / Node | optimized | 228.5 | Completed | 41.0 | 500.4 | 8.8 | 2 |
| TypeScript / Node | maintenance | 72.6 | Completed | 33.0 | 253.6 | 3.0 | 0 |
| Go | initial | 124.1 | Completed | 24.8 | 309.6 | 7.0 | 0 |
| Go | optimized | 231.0 | Completed | 40.1 | 532.4 | 7.0 | 1 |
| Go | maintenance | 83.8 | Completed | 51.3 | 287.6 | 4.1 | 1 |
| Rust | initial | 123.2 | Completed | 21.1 | 220.4 | 7.6 | 0 |
| Rust | optimized | 360.0 | Timed out | Unknown | Unknown | Unknown | 3 |
| Rust | maintenance | 85.1 | Completed | 40.9 | 430.1 | 4.8 | 1 |
| Swift | initial | 181.3 | Completed | 25.5 | 212.2 | 8.0 | 1 |
| Swift | optimized | 213.1 | Completed | 37.5 | 809.2 | 10.7 | 1 |
| Swift | maintenance | 82.5 | Completed | 37.9 | 369.4 | 3.5 | 1 |
| Kotlin / JVM | initial | 174.5 | Completed | 73.0 | 359.6 | 8.6 | 1 |
| Kotlin / JVM | optimized | 360.0 | Timed out | Unknown | Unknown | Unknown | 1 |
| Kotlin / JVM | maintenance | 60.3 | Completed | 33.9 | 170.0 | 2.8 | 1 |
| MoonBit native | initial | 302.9 | Completed | 47.3 | 1055.4 | 10.7 | 4 |
| MoonBit native | optimized | 360.0 | Timed out | Unknown | Unknown | Unknown | 1 |
| MoonBit native | maintenance | 212.9 | Completed | 40.0 | 377.2 | 4.3 | 0 |
| BAML | initial | 209.3 | Completed | 48.5 | 821.5 | 11.4 | 1 |
| BAML | optimized | 274.2 | Completed | 70.9 | 939.4 | 9.7 | 3 |
| BAML | maintenance | 189.4 | Completed | 39.0 | 562.9 | 4.6 | 2 |
| Zerolang | initial | 408.7 | Completed | 45.2 | 1958.7 | 15.2 | 21 |
| Zerolang | optimized | 360.0 | Timed out | Unknown | Unknown | Unknown | 20 |
| Zerolang | maintenance | 185.1 | Completed | 59.6 | 672.9 | 4.0 | 2 |

Python had the shortest initial authoring time and lowest initial uncached input/output in this deep task. MoonBit/BAML/Zero did not demonstrate token savings here. Discovery packets, tool behavior, differing context sizes and concurrency confound any broad claim about syntax efficiency. The four optimization timeouts have no final usage receipt; an overall dollar-cost ranking would therefore be unsupported. Command failures include exploratory lookups and shell errors, not only compiler defects.

## Pilot outcomes

Two starts per language, each with initial and interval-merging extension turns. Initial 69 and extension 89 checks yield 316 repeated observations per language. Every language passed these checks. More varied/larger inputs subsequently exposed issues absent from the initial set.

| Language | Checks passed | Median initial + change s | Four-turn uncached kTok | Four-turn output kTok | Nonzero commands |
|---|---|---|---|---|---|
| Python | 316/316 | 105.7 | 102.1 | 10.4 | 0 |
| TypeScript / Node | 316/316 | 124.3 | 102.8 | 12.5 | 0 |
| Go | 316/316 | 186.0 | 95.2 | 18.8 | 5 |
| Rust | 316/316 | 148.7 | 94.1 | 11.2 | 2 |
| Swift | 316/316 | 188.5 | 93.4 | 14.1 | 3 |
| Kotlin / JVM | 316/316 | 154.6 | 93.1 | 12.2 | 1 |
| MoonBit native | 316/316 | 171.2 | 129.0 | 15.0 | 3 |
| BAML | 316/316 | 157.7 | 155.9 | 14.4 | 5 |
| Zerolang | 316/316 | 505.1 | 186.8 | 35.7 | 20 |

In larger pilot inputs, six mainstream languages plus BAML passed 10/10 workload/trial combinations; MoonBit passed 8/10 and Zero 4/10. MoonBit trial one used default shortlex string ordering where task-required lexicographic ordering needed an explicit comparator. Zero had larger-workload timeouts. Prepared execution removed launcher/build overhead without repairing business logic. These failures belong to the particular generated implementations and transport, not inherent language capacity limits. The [pilot report](../archive/pilot/reports/Evaluation_Report.md), [runtime records](../archive/pilot/results/runtime_performance.json), [prepared records](../archive/pilot/results/prepared_performance.json) and [sorting probe](../archive/pilot/results/sorting_probe.json) retain details. The deeper tasks changed the observed CPU ordering, so a pilot ranking should not be generalized.

## Supplementary Python/NumPy

One separate extra-budget 180-second prompt produced a NumPy telemetry path after the equal-budget comparison. Final validation and six follow-up runs passed. Supported telemetry median CPU was 1.071 seconds versus 2.383 for the main Python worker; RSS was approximately 27.4–27.5 MiB versus 14.4–15.1 across main workloads. Invoice/log business computation was unchanged, though importing NumPy changes process context.

The approximately 2.2× observed telemetry reduction is informative about a native-library option, not a randomized causal effect. It received extra authoring budget, ran later and adds a compiled dependency. It is excluded from the equal-budget nine-language comparison. Python JSON parsing/array conversion remain in the timed process. [Supplementary records](../archive/deep/results/numpy_reference.json), [source](../archive/deep/supplementary/python_numpy/).

## Practical interpretation, not a universal tier list

Established ecosystems remain sensible defaults: TypeScript for browser/full-stack work where one language simplifies operation; Go for standalone portable services/CLIs; Rust for resource-control needs; Swift/Kotlin for their native platforms; Python where automation/scientific libraries fit. These are engineering judgments with different evidence from the runtime tables. UI, HTTP concurrency, device packaging and energy were not measured.

MoonBit's low native RSS and BAML's permissive source/host integration justify bounded experiments. They do not demonstrate an overall replacement advantage. Zero's experimental status plus incomplete task correctness argues against using it as a main production foundation today. Future releases, different models and better implementations could change these judgments.
