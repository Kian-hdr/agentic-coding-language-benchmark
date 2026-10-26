# Final report evidence review

Read-only QA, 27 October 2026. Reviewed `deep_phase/Deep_Evaluation_Report.md`, `Summary.json`, `Measurement_Tables.md`, raw stage/build/validation/agent reports, long-run and NumPy records, and protocol. No benchmarks rerun or business source changed. Only this review was written.

**No material correction required in the reviewed report.**

- Independently recomputed long-run medians/minima/maxima and correct/supported counts from raw records for every language/workload; they agree with Summary and the rounded tables. Source hashes in Summary matched the retained raw files at review time.
- All three standard stages have 297 scheduled records. Each of the eight non-Zero candidates passed 33 performance records at every stage. Final validation is four datasets/221 expected responses per language; eight pass all, Zero passes two of four despite a successful final build.
- Long pass: 54 scheduled, 48 correct, six explicit Zero skips, zero timeouts/pending. Exactly two correct records lack supported resource accounting: Kotlin telemetry repetition 0 and BAML invoice repetition 1. Their CPU/RSS are excluded, the associated cells are correctly marked n=1, leaving 46 supported records.
- TypeScript has the lowest supported median CPU for each of these three generated long-worker implementations. Rust has the lowest observed supported RSS range. The report consistently restricts these observations to the generated programs on this Mac, discloses startup/JIT/IO, and does not claim intrinsic language speed, HTTP tail latency or energy performance.
- Recomputed all per-stage token aggregates against actual agent usage receipts. Optimization timeout/missing-receipt cases are correctly listed for Rust, Kotlin, MoonBit and Zero. Missing consumption is treated as unknown, not zero. Authoring/token figures are separated from compute metrics.
- Dataset scales agree with long-run metadata: 4,096 requests each; 2,097,152 invoice/log events and 16,777,216 telemetry samples. NumPy telemetry median/RSS and its separate extra-budget status are accurately reported.
- Compatibility now explicitly has lower decision weight and concerns required current flagship targets. macOS13/Intel/older-runtime probes are labeled deployment observations, not ranking rewards. Modern-device installation/UI/battery gaps remain explicit. Platform recommendations are ecosystem judgments with clear untested full-app boundaries.
- Production tiers clearly distinguish established-language defaults, bounded MoonBit/BAML experiments and Zero's exclusion. Continued-support judgments use qualitative stewardship/source/exit evidence without invented survival probabilities or binding guarantees. GPT-6.1-specific training is not inferred from skills, marketing or local success.
- One generated application per language, two long repetitions (including n=1 cells), non-laboratory host conditions, context-size differences, extra NumPy budget and untested production/device domains are all disclosed. The report does not turn these samples into statistical reliability estimates.

Reviewed document hashes:
- `Deep_Evaluation_Report.md`: `00a618b47a0498f8ad746ef800d28cb4270bf42f1e7e1c46a47f7be93b3f8aef`
- `Summary.json`: `fb9594c37ce5495018a623afbb4eaa31e603213b41526e575e9fd32391412e49`
- `Measurement_Tables.md`: `19e687d97346c12525353e2af0bb74e68dfa30915428df7ac718cde7744f8d14`
