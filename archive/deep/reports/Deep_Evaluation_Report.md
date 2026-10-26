# Programming languages for software written by Codex GPT-6.1 Sol

Research and experiments: October 26–27, 2026. Recommendation for new work, not an instruction to migrate an existing product.

## Decision

**TypeScript is my default for Codex-authored public web applications. Go is my default for portable services and CLIs. Rust is my first choice for memory-constrained native components.** Swift and Kotlin remain the strongest fits for native Apple and Android apps, respectively; Python remains an excellent automation and scientific-computing choice when its native-library ecosystem fits the workload.

The deeper measurements changed the earlier pilot's speed ordering. In the final longer batches, the generated TypeScript/Node implementation used the least supported CPU time in all three workloads. Rust used the least peak resident memory, approximately 2.2–2.6 MiB versus TypeScript's 65.2–83.6 MiB. This is an implementation/runtime comparison on this Mac, not a claim that JavaScript inherently beats Rust. The earlier [pilot report](../Evaluation_Report.md) remains a historical result for different tasks and shorter processes.

Among specialized languages, **MoonBit is the most interesting resource-efficient experimental candidate; BAML is the most attractive permissively licensed, agent-focused integration experiment.** Neither demonstrated an overall adoption advantage over established languages under these priorities. Zerolang is unsuitable for a production migration on the evidence collected.

### Final KPI priorities

The user clarified after testing that compatibility is secondary: support current flagship devices relevant to the product, without rewarding support for extremely old hardware. This changes the adoption rubric, not the recorded experiments.

| KPI | How it affects this decision | What was measured or researched |
|---|---|---|
| Correctness and reliability | Required before speed credit; principal priority | Independent expected outputs, malformed-input recovery, request isolation, safe integer boundaries, regression and maintenance change |
| Compute efficiency | Principal priority | Whole-worker CPU seconds, peak RSS, input size scaling, startup-inclusive batch wall time; no energy or server tail-latency measurement |
| Continued support and exit cost | Principal priority | Current releases, stewardship, compatibility policies, source/license availability, recoverable toolchains, ecosystem and portability boundaries |
| Agent effort and cost | Secondary quantitative dimension | Actual GPT-6.1 Sol authoring/change time, input/cache/output receipts, command failures and timeout status |
| Development and maintenance usability | Secondary | Reproducible builds, diagnostic/API discovery friction, ability to implement one backward-compatible feature |
| Compatibility | Practical check for required modern targets, lower ranking weight | Documented OS/framework/runtime support, selected cross-builds and alternate-runtime smoke tests; clean target-device installation untested |

There is no invented overall weighted score. A product must first satisfy correctness and its actual target requirements; compare CPU, memory, support and effort among eligible options. An absent Windows UI pathway matters for a Windows app, while lack of old-CPU support does not matter for a current flagship-only deployment.

## Per-use-case tier list

S means recommended starting point for that use case. A means strong alternative with a concrete tradeoff. B means bounded experiment requiring product qualification. D means avoid adopting as the main production language today. These are decision tiers, not measured probabilities.

| Use case | S tier / winner | A tier / alternative | Basis and compatibility boundary |
|---|---|---|---|
| Public browser apps and typical web products | **TypeScript** | Existing backend language paired with TypeScript UI | Native JavaScript/browser ecosystem; favorable observed CPU and agent results. Browser rendering, accessibility and UI were not benchmarked here. |
| Portable backend services and distributable CLIs | **Go** | Rust; TypeScript when Node fits deployment | Go's standard tooling, source compatibility and simple per-target binaries are useful. This worker cross-built for modern Windows/Linux x64 and ARM64. No network-service load test was run. |
| Lowest resident memory and native systems components | **Rust** | Go; Swift for Apple-centric integration | Strongest observed memory economy and competitive CPU; explicit ownership/type checks. CPU profiling and extra independent implementations could change the CPU ordering. |
| These exact sustained JSON batch workloads, CPU priority | **TypeScript/Node** | Rust, especially with a tight memory budget | Lowest observed final CPU across all three; 2/2 supported repetitions per workload. This is the measured niche, not a universal language ranking. |
| Native iPhone/iPad/Mac apps | **Swift** | Kotlin Multiplatform for explicitly qualified shared code | Native Apple framework fit; the CLI test does not measure SwiftUI responsiveness or battery. Current-device support is the relevant target, not legacy reach. |
| Native Android apps | **Kotlin** | TypeScript mobile framework when native bridges meet the product needs | Android ecosystem/platform fit. The tested JVM21 JAR is not an Android APK and its memory result must not be applied to Android. |
| Automation, data science, existing ML/scientific libraries | **Python plus suitable native libraries** | TypeScript for integrations; Rust for isolated kernels | Shortest observed initial/change authoring; strong ecosystem. Pure-Python loops and vectorized NumPy are different deployment/compute paths. |
| Shared desktop app across current Windows/macOS/Linux | **TypeScript with a qualified desktop framework** | Rust core plus web UI; Kotlin/JVM desktop | Framework/package/runtime choice controls support and memory. Electron or Tauri must be evaluated as a full stack; Node worker RSS is not desktop-app RSS. No desktop UI benchmark performed. |
| New language with low-memory native/Wasm potential | **No production S tier** | **MoonBit: B**, isolated module pilot | Low measured RSS, multiple backends and substantial tooling; evolving APIs, native IO and compiler independence need qualification. |
| New language explicitly oriented to agent workflows and host integration | **No production S tier** | **BAML: B**, isolated module pilot | Passed the deep functional/maintenance suite and has permissive source and host bridges; much higher CPU here, pre-1.0 application tooling. |
| Zerolang as primary production language | **D** | Established language | Compiler/build friction and incomplete final correctness; upstream's experimental/security warning. |

For a single default across a web-oriented portfolio, choose **TypeScript**, adding a Go service or Rust component only when measured constraints justify it. For an infrastructure-oriented portfolio, start with **Go**. For native mobile, use the platform language. This is a stronger recommendation than selecting one syntax for every layer.

## What was actually tested

Nine languages received a new multi-operation application authored by the actual Codex CLI using `gpt-6.1-sol`, medium reasoning: initial implementation (720-second cap), repair/optimization (360 seconds), then backward-compatible maintenance (240 seconds). That is 27 main model turns, separate from the earlier 36-turn pilot. One generated application per language is not a statistical sample of that language's agent reliability. Some authoring ran concurrently, so authoring time includes service/tool latency and host contention.

All business computation and JSON/file processing stayed in the assigned language, with approved JSON/IO dependencies. Builds were optimized/release and excluded from runtime timings. Version-matched packets gave tool paths and API hints; packet/documentation sizes differed, so token totals also reflect discovery context. No manual fixes to candidate business logic were applied after scoring.

Three operations share a persistent JSONL file worker: invoice reconciliation/deduplication; access-log aggregation with exact nearest-rank p95; rolling integer telemetry analytics. The maintenance request added per-paid-event fees while preserving the original response schema when the option is absent. Tests included malformed JSON followed by valid requests, mixed operations, long strings/lines, CRLF, final unterminated lines, ASCII lexical ordering, values beyond 32-bit, and held-out values near the safe 53-bit boundary. These are realistic application components, not an HTTP service or native consumer app.

Measurements ran one worker at a time on this Apple Silicon Mac, randomized across languages/datasets, with warm filesystem cache and declared numerical-library thread counts. `wait4` captured child user+system CPU and process peak RSS; Darwin reports RSS in bytes. The wrappers were independently checked to execute prebuilt programs. OS power modes and unrelated work were not altered. The host was not a dedicated laboratory machine.

The standard stage measurements contain 297 scheduled records per stage: five repetitions for six medium/large workloads plus three empty baselines, across nine languages. All eight non-Zero candidates passed 33/33 performance cases at each stage. Zero had build failures initially/after optimization and incomplete final validation. Skips remain explicitly unmeasured.

The final longer follow-up increased each workload eightfold and transformed records to defeat trivial full-request caching. Each file contains 4,096 requests: invoice and logs each process 2,097,152 events, telemetry 16,777,216 samples. There were 54 scheduled records: 48 correct runs, six eligibility skips for Zero, no timeouts or pending records. Two correct-output records had unsupported process-tree resource accounting and are excluded from CPU/RSS summaries, leaving 46 supported resource records. Exact prompts, frozen source, outputs/hashes and all raw measurements are retained.

## Final CPU and memory results

Values are CPU seconds for a whole final batch, median of two supported runs except the two explicitly marked n=1. They include parsing, computation, file IO, startup/JIT and shutdown. Peak RSS ranges span the supported runs across the three workloads.

| Language/runtime | Invoice CPU s | Log CPU s | Telemetry CPU s | Peak RSS MiB |
|---|---:|---:|---:|---:|
| TypeScript / Node | **0.544** | **0.507** | **0.327** | 65.2–83.6 |
| Rust | 0.689 | 0.561 | 0.387 | **2.2–2.6** |
| Go | 1.051 | 1.045 | 0.622 | 5.5–12.1 |
| Python, standard library | 1.064 | 1.366 | 2.383 | 14.4–15.1 |
| Swift | 1.711 | 1.633 | 0.548 | 9.1–9.6 |
| Kotlin / JVM21 | 2.027 | 1.727 | 1.022, n=1 | 184.3–312.6 |
| MoonBit, native | 1.202 | 1.781 | 0.648 | 3.6–4.4 |
| BAML | 5.313, n=1 | 6.363 | 2.088 | 86.3–100.8 |
| Zerolang | Ineligible | Ineligible | Ineligible | Ineligible |

Two repetitions provide observed ranges, not tight confidence intervals. TypeScript's individual CPU ranges were 0.536–0.551, 0.501–0.512 and 0.326–0.329 seconds. Rust's were 0.638–0.741, 0.561–0.562 and 0.376–0.398. MoonBit's log CPU varied from 1.218 to 2.345 seconds. Scheduling/runtime/IO causes were not individually profiled. BAML invoice repetition 1 and Kotlin telemetry repetition 0 retain correctness credit but no comparable resource credit because extra process-group members were observed. The remaining cells must not silently treat those rows as supported.

**Why TypeScript can win here:** source review found normal JSON parsing, per-request maps/sets, selection and a linear rolling-window algorithm, with no hardcoded answers or cross-request output cache. Rust's generated parser can inspect the request body during envelope validation and again during typed extraction. These choices make the observed result plausible. They do not establish intrinsic language speed limits. Rust's lower memory is a separate, substantial advantage. [Independent validity review](../deeper_research/Deep_Validity_Review.md)

The smaller original deep batches favored Rust CPU more often. Increasing the batch length changed relative startup/JIT weight and the ranking; this is exactly why a single tiny benchmark is insufficient. The long pass still does not establish an indefinitely warm JVM/Node steady state. Initial versus optimized code improved several implementations substantially: for example, Swift invoice RSS fell from approximately 65 to 9 MiB on the same large dataset, while BAML log CPU fell from about 2.316 to 0.657 seconds. Ordinary implementation improvement matters before language migration. [All stage tables and counters](Summary.json)

### Native-library Python follow-up

The main Python optimization turn was allowed to use the staged NumPy environment but kept standard-library code. A separate extra 180-second targeted prompt then produced a NumPy telemetry kernel. All final validation files and six follow-up long runs passed. Median telemetry CPU was approximately **1.071 seconds versus 2.383** for the main Python implementation; RSS rose to about **27.4–27.5 MiB**. Invoice/log computation was unchanged.

This illustrates an approximately 2.2x observed telemetry reduction from a native-library path, not a randomized causal estimate: the supplementary runs occurred later and used an extra prompt/dependency. It is excluded from the equal-budget nine-language ranking. Python with NumPy still includes Python JSON parsing and array conversion, so this does not measure a pure native numerical kernel. NumPy's compiled array operations explain why “Python always wastes compute” is too broad. [NumPy documentation](https://numpy.org/doc/stable/user/whatisnumpy.html), [supplementary records](results/numpy_reference.json)

## Reliability, agent cost and usability

Eight candidates rebuilt successfully and passed all four final validation datasets: 221 request/response cases per language, plus the repeated performance datasets and longer follow-up. Zero rebuilt at the end and passed the fee/numeric files, but failed long-customer-string behavior in the original and formatting datasets. It was therefore excluded from the overall performance ranking even though individual performance cases passed. Its earlier native backend argument-slot limitation was a real build obstacle in this experiment; this does not prove the language can never implement the workload.

All nine initial and maintenance turns completed within their caps. Optimization turns for Rust, Kotlin, MoonBit and Zero timed out; their final optimization usage receipts are absent. This is a model-turn failure/unknown cost, distinct from whether source left on disk compiled and passed later checks. All eight eligible languages preserved the required behavior after maintenance; a single successful change does not estimate multi-year defect rates.

| Language | Initial / maintenance time s | Initial uncached input kTok | Initial cached input kTok | Initial output kTok |
|---|---:|---:|---:|---:|
| Python | **97.4 / 45.4** | **19.5** | 142.2 | **4.7** |
| TypeScript | 160.0 / 72.6 | 30.6 | 235.3 | 6.8 |
| Go | 124.1 / 83.8 | 24.8 | 309.6 | 7.0 |
| Rust | 123.2 / 85.1 | 21.1 | 220.4 | 7.6 |
| Swift | 181.3 / 82.5 | 25.5 | 212.2 | 8.0 |
| Kotlin | 174.5 / 60.3 | 73.0 | 359.6 | 8.6 |
| MoonBit | 302.9 / 212.9 | 47.3 | 1,055.4 | 10.7 |
| BAML | 209.3 / 189.4 | 48.5 | 821.5 | 11.4 |
| Zero | 408.7 / 185.1 | 45.2 | 1,958.7 | 15.2 |

Input counts accumulate repeated model calls/context within the turn. Cached input is included in reported input and remains a cost category, not free work. Reasoning counters are preserved separately without blindly double-counting them as extra output. Missing optimization receipts mean unknown consumption, never zero. No full-cost league table or dollar savings is inferred from incomplete receipts or subscription usage. [Recomputed tables](Measurement_Tables.md), [machine-readable summary](Summary.json)

Python had the lowest observed initial authoring time and lowest uncached input/output here, consistent with the earlier two-start pilot. BAML, MoonBit and Zero did not demonstrate token savings in these experiments. This is evidence about this model/toolchain/context, not knowledge of proprietary training data. Official Codex skills and usable CLI diagnostics establish workflow compatibility; they do not establish that GPT-6.1 Sol was trained or specially optimized for a language. No inspected primary source supplied a controlled GPT-6.1 Sol result that supersedes these local measurements.

## Continued support and maturity

Long-term involvement cannot be guaranteed by a benchmark or company logo. The useful evidence is governance, source recoverability, compatibility policy, active maintenance, multiple maintainers and the ability to hire or exit.

- **Go, Rust, TypeScript, Python, Swift and Kotlin:** established production ecosystems with public toolchains, institutional stewardship and existing deployment paths. Go's source compatibility policy is especially explicit. Rust has independent foundation support; Kotlin has a multi-organization foundation and compatibility review; Python has PSF stewardship. Dependencies/frameworks retain their own lifecycles. These are lower adoption-risk signals, not perpetual support contracts. [Go policy](https://go.dev/doc/go1compat), [Rust Foundation](https://rustfoundation.org/about/), [Kotlin governance](https://kotlinfoundation.org/structure/), [PSF](https://www.python.org/psf/about/), [TypeScript source](https://github.com/microsoft/TypeScript), [Swift project](https://www.swift.org/about/)
- **MoonBit:** the broadest compiler/build/package/backend stack among the three specialized candidates evaluated. An institutional team and active tools/core are credible engineering signals. The evaluated compiler was pre-1.0; current compiler source publication lagged the binary, and the compiler uses custom public-source terms. Generated applications can use the developer's chosen license; the concern is independent compiler maintenance/exit cost, not a blanket ban on public apps. Its low RSS deserves an isolated pilot, not a codebase-wide migration. [Compiler and license](https://github.com/moonbitlang/moonbit-compiler), [toolchain audit](../docs/moonbit.md)
- **BAML:** the current general-purpose agent-oriented language, not merely its older prompt DSL. It has Apache-2.0 source, active company development, deployment assets and host bridges. It passed the deeper functional task; its current VM/runtime CPU and broader application/tooling maturity were less attractive here. It is a useful isolated integration experiment with a more permissive fork path. [Official repository](https://github.com/BoundaryML/baml), [versioned release](https://github.com/BoundaryML/baml/releases/tag/baml-language-0.23.0)
- **Zerolang:** a real Vercel Labs experiment with tooling, not an anonymous demo, but its own repository warns about breaking changes/security and advises isolation from production/sensitive data. Branding establishes no binding support commitment. Current local failures reinforce its experimental tier. [Official status](https://github.com/vercel-labs/zerolang)

No inspected evidence established a binding multi-year support agreement or funded runway for MoonBit, BAML or Zero. Avoid numerical vendor-survival probabilities. A retained compiler archive can reproduce today's build; it does not maintain compatibility with future OS/security changes. [Detailed support/platform research](../deeper_research/Maintenance_and_Use_Cases.md)

## Compatibility for current public devices

Compatibility has a lower decision weight under the user's final clarification. We do not penalize a language for dropping extremely old hardware. We still check the complete product stack on the modern targets actually promised: language, libraries, UI framework, OS/CPU, runtime, installer, signing and updates.

Actual evidence collected:

- **Go:** the final source cross-built successfully for Linux and Windows, x64 and ARM64, with CGO disabled. File formats/architectures were inspected. The artifacts were not executed on those OSs.
- **Swift:** separate ARM64 and x86_64 builds explicitly targeted macOS13 and combined into a universal binary. A six-request x86_64 smoke test passed using existing Rosetta on this Mac. This is not a physical Intel-device or macOS13 execution test. The original default build declared macOS27.2; the explicit variants declared13.0. This is a deployment-setting observation, not a penalty for current-device-only software.
- **Python:** the final source passed six-request local smoke tests under installed Python3.12 and3.13, in addition to the main3.14 run. The compiled `.pyc` is version-specific and was not passed between versions.
- **TypeScript and Kotlin:** local Node26 and JVM21 smoke tests passed. These do not establish browser/mobile support for the generated worker. The JVM JAR needs an appropriate runtime; it is not an Android package.
- **Other native artifacts:** load-command inspections recorded actual macOS floors. A metadata parser initially overwrote minimum OS with nested linker versions; corrected records were regenerated from retained raw output, with originals preserved and no benchmarks rerun. [Correction review](../deeper_research/Compatibility_Review.md)

Documented pathways include TypeScript/JavaScript in browsers, Go/Rust native desktop/server targets, Swift's Apple/native platform support, and Kotlin's Android/JVM/multiplatform paths. UI framework support is separate: Swift's Windows/Linux compiler availability does not bring SwiftUI to those systems. BAML/MoonBit bridges or Wasm outputs also need a complete host application and dependency matrix. [Swift platform support](https://www.swift.org/platform-support/), [Rust target tiers](https://doc.rust-lang.org/rustc/platform-support.html), [Go targets](https://go.dev/doc/install/source), [Kotlin target tiers](https://kotlinlang.org/docs/native-target-support.html)

**No clean Windows/Linux/phone installation, app-store package, accessibility/UI, update/rollback or battery test was performed.** Those are product-specific release checks, not reasons to turn old-device compatibility into a dominant language metric. Modern flagship support remains documented or cross-built where stated, rather than certified by these CLI experiments. [Raw compatibility records](compatibility/results.json)

## Other serious candidates and limits of the shortlist

C#/.NET, Java and C++ remain serious choices for their existing ecosystems; they were researched but not included in the nine-language runtime experiment. C# deserves a product-specific comparison for .NET/Windows/Unity work; Java for existing JVM services; C++ for required native/game SDKs. Their absence is not a claim that they lose.

Mojo is worth evaluating for numerical CPU/GPU kernels. Current official documentation shows1.2.0 and open-source availability, so old descriptions of it as closed/pre-1.0 are stale. Its documented environment includes modern Apple Silicon macOS and specified Linux CPUs; native Windows is not supported, WSL is documented. Modern hardware minima are acceptable under the final brief, but the required target/runtime still matters. It was not benchmarked here and receives no measured performance rank. [Mojo requirements](https://mojolang.org/docs/requirements/), [additional candidate analysis](../deeper_research/Maintenance_and_Use_Cases.md)

## Adoption decision and remaining evidence

Keep established-language defaults. Use TypeScript for public web/app work, Go for portable services/tools, Rust when memory/control constraints earn the extra implementation complexity, and Swift/Kotlin for native platform apps. Keep Python where its ecosystem and authoring advantage provide value, then profile/vectorize or replace only demonstrated hot paths. A replacement must repay development, integration, validation, operation and eventual exit costs, not just save tokens in a toy snippet.

The next experiment before a real migration should use the actual product, repeated independent implementation/maintenance tasks, representative production traces, target-device packages and a dedicated measurement window. HTTP p95/p99, concurrency, security failures, energy, GPU workloads and multi-year maintenance remain unmeasured. Current passing tests support the stated task contracts, not a universal reliability certification. Nothing here requires or authorizes rewriting an existing codebase.

### Evidence index

- [Protocol](PROTOCOL.md), [task specification](SPEC.md), [oracle](oracle.py), [agent runner/prompts](agent_runs.py), [measurement harness](measure.py)
- [Recomputable summary script](summarize.py), [summary JSON](Summary.json), [all measurement tables](Measurement_Tables.md)
- [Long-run records](results/long_run.json), [NumPy records](results/numpy_reference.json), [compatibility records](compatibility/results.json)
- [Source/oracle review](../deeper_research/Oracle_Review.md), [measurement review](../deeper_research/Measurement_Review.md), [final independent validity review](../deeper_research/Deep_Validity_Review.md)
- Per-stage sources: `artifacts/LANGUAGE/STAGE/source/`; actual prompts and model event/usage receipts: `runs/LANGUAGE/`; raw build, validation and performance records: `results/`.

Accuracy: 90% | Evidence: strong | Main uncertainty: one generated application per language and untested full-app/device behavior
