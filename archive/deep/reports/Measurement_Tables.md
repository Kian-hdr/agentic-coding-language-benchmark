# Recomputed measurement tables

CPU seconds include full worker lifetime. Cells require correct output and supported resource accounting. Two long-run repetitions, except marked n=1. RSS is process peak resident memory, not private/billable memory.

| Language | Invoice CPU s | Access log CPU s | Telemetry CPU s | Peak RSS range MiB |
|---|---:|---:|---:|---:|
| Python | 1.064 | 1.366 | 2.383 | 14.4–15.1 |
| TypeScript | 0.544 | 0.507 | 0.327 | 65.2–83.6 |
| Go | 1.051 | 1.045 | 0.622 | 5.5–12.1 |
| Rust | 0.689 | 0.561 | 0.387 | 2.2–2.6 |
| Swift | 1.711 | 1.633 | 0.548 | 9.1–9.6 |
| Kotlin/JVM | 2.027 | 1.727 | 1.022 (n=1) | 184.3–312.6 |
| MoonBit | 1.202 | 1.781 | 0.648 | 3.6–4.4 |
| BAML | 5.313 (n=1) | 6.363 | 2.088 | 86.3–100.8 |
| Zerolang | ineligible | ineligible | ineligible | ineligible |

Invoice and access log each contain 2,097,152 events; telemetry contains 16,777,216 samples. Each file has 4,096 requests.

| Language | Initial / maintenance seconds | Initial uncached input kTok | Initial cached input kTok | Initial output kTok | Optimization turn |
|---|---:|---:|---:|---:|---|
| Python | 97.4 / 45.4 | 19.5 | 142.2 | 4.7 | completed |
| TypeScript | 160.0 / 72.6 | 30.6 | 235.3 | 6.8 | completed |
| Go | 124.1 / 83.8 | 24.8 | 309.6 | 7.0 | completed |
| Rust | 123.2 / 85.1 | 21.1 | 220.4 | 7.6 | timed out; usage unknown |
| Swift | 181.3 / 82.5 | 25.5 | 212.2 | 8.0 | completed |
| Kotlin/JVM | 174.5 / 60.3 | 73.0 | 359.6 | 8.6 | timed out; usage unknown |
| MoonBit | 302.9 / 212.9 | 47.3 | 1055.4 | 10.7 | timed out; usage unknown |
| BAML | 209.3 / 189.4 | 48.5 | 821.5 | 11.4 | completed |
| Zerolang | 408.7 / 185.1 | 45.2 | 1958.7 | 15.2 | timed out; usage unknown |

Token units are decimal. Cached input remains input and is not free. Missing receipts are unknown. Reasoning counters are retained in Summary.json; do not blindly add them to output if included by the provider.

## Individual supported long-run observations

| Language | Workload | CPU seconds | Peak RSS MiB |
|---|---|---|---|
| Python | invoice | 1.1099, 1.0178 | 15.0, 15.0 |
| Python | access_log | 1.4035, 1.3279 | 15.1, 15.1 |
| Python | telemetry | 2.4099, 2.3556 | 14.8, 14.4 |
| TypeScript | invoice | 0.5510, 0.5364 | 83.2, 82.9 |
| TypeScript | access_log | 0.5123, 0.5010 | 83.6, 83.2 |
| TypeScript | telemetry | 0.3292, 0.3258 | 65.4, 65.2 |
| Go | invoice | 1.1047, 0.9975 | 11.6, 12.0 |
| Go | access_log | 1.0986, 0.9923 | 11.2, 12.1 |
| Go | telemetry | 0.6800, 0.5633 | 5.5, 6.0 |
| Rust | invoice | 0.6377, 0.7410 | 2.6, 2.6 |
| Rust | access_log | 0.5609, 0.5616 | 2.4, 2.4 |
| Rust | telemetry | 0.3757, 0.3979 | 2.2, 2.2 |
| Swift | invoice | 1.9046, 1.5165 | 9.5, 9.6 |
| Swift | access_log | 1.5766, 1.6902 | 9.5, 9.6 |
| Swift | telemetry | 0.5888, 0.5075 | 9.1, 9.1 |
| Kotlin/JVM | invoice | 1.6996, 2.3537 | 292.9, 307.1 |
| Kotlin/JVM | access_log | 1.6674, 1.7862 | 312.6, 297.0 |
| Kotlin/JVM | telemetry | 1.0217 | 184.3 |
| MoonBit | invoice | 1.1711, 1.2324 | 4.2, 4.3 |
| MoonBit | access_log | 1.2177, 2.3451 | 4.4, 4.3 |
| MoonBit | telemetry | 0.6203, 0.6758 | 3.7, 3.6 |
| BAML | invoice | 5.3132 | 88.5 |
| BAML | access_log | 5.9968, 6.7296 | 95.1, 100.8 |
| BAML | telemetry | 2.0538, 2.1227 | 86.4, 86.3 |
