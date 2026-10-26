# Limitations and interpretation boundaries

## Sampling and causal inference

The deep phase contains **one generated application per language**. The pilot has two fresh starts per language on a different, smaller specification. Runtime repetitions sample execution variability of fixed programs, not model-authoring variation. Twenty runtime observations are not twenty independent programs. Task families share IO, JSON and aggregation characteristics. No population-level agent reliability rate, significance claim or universal language ranking is justified.

These implementations differ in algorithms, parsing, allocation, libraries and runtime configuration. The comparison evaluates those delivered implementations under bounded budgets. It cannot separate a language effect from model familiarity, compiler feedback, documentation, library quality, the chosen algorithm or chance. Timeout budgets favor work completed promptly and do not establish eventual impossibility. Before/after optimization is not randomized, and final long follow-ups ran later on the same host.

## Historical model and context reproducibility

The recorded authoring model alias is `gpt-6.1-sol`, medium reasoning, through the then-installed Codex CLI. It was available in that local session. Public access to the same alias/backend is not guaranteed; proprietary routing/model weights can change. No claim about the model's training corpus or special language tuning follows from local success or an official skill.

Historical flags such as `--ignore-user-config` and disabled integrations document the intended controls. They do **not prove absence of every system instruction, global AGENTS instruction, startup tool context or account-level setting**. The actual complete hidden system prompt and environment are not reconstructible from the published user prompts. Startup warnings and provider/tool differences can affect context and tokens. Private global instructions, account settings and raw agent transcripts are intentionally not published. Future re-authoring is a new experiment, not an exact replay.

## Measurement

All historical runtime results come from one Apple Silicon Mac in a normal working environment, not a dedicated controlled laboratory. Warm-cache, sequential randomized execution reduces some variation but does not remove host contention, OS scheduling, thermal behavior, filesystem effects or runtime variability. Power/energy and ambient conditions were not controlled or measured.

CPU is whole-process user + system time; wall time and RSS include startup, parsing, IO, JIT and shutdown. Longer batches reduce relative startup effects but do not establish warm-server steady state. Peak RSS is resident process memory, not live/private heap, aggregate tree memory, app footprint or billing cost. A high-water mark over two samples does not establish leak-free behavior.

Process-tree observation is best effort. Two final correct-output records showed extra process-group members; exclude their CPU/RSS and mark the corresponding BAML invoice and Kotlin telemetry cells n=1. Do not silently reuse excluded values. Remaining supported values are not a certification that no short-lived descendant existed. Independent source/wrapper review is an additional check, not security isolation proof.

Two final long repetitions are too few for tight uncertainty estimates; raw values/ranges are published. Invoice events, log events and telemetry samples are different workload units. CPU-per-million figures must be interpreted within workload, not pooled into a single efficiency score.

## Correctness and reliability

The external oracle and tests are finite, written within this project and reviewed with AI assistance. Passing them is not formal verification, human acceptance, security certification or proof against all inputs. Shared misunderstandings between specification, generator and oracle remain possible. Published cases now become public training material; a new benchmark must use genuinely new holdouts if it needs a contamination-resistant claim.

No task-running agent was supposed to inspect evaluation files or other runs. Reviewed logs/source showed no obvious answer copying, outsourced business computation or full-request result cache. This is not an adversarial containment audit. Omitted raw transcripts limit public trace-level verification. Maintained source/tests and selected diagnostics still permit independent functional inspection.

One backward-compatible fee feature tests a particular maintenance operation, not multi-year maintainability, team onboarding, dependency upgrades or defect rates. Zero's failed final validation is reported rather than converted into a measured speed ranking. A failure of these programs is not proof that their language can never implement the task.

## Agent effort and money

Reported input counters include repeated context across calls; cached input remains input and a cost category. Packet size/API discovery and ambient tool context differ. Short source is not evidence of fewer total model tokens. Authoring wall time includes network, service latency, compilation/testing and some concurrent host activity.

Optimization turns for Rust, Kotlin, MoonBit and Zero timed out without final usage receipts. Their usage is unknown, not zero. No complete dollar-cost leaderboard or subscription-usage saving is inferred. The supplementary NumPy turn used extra budget and an additional dependency, so its result is not equal-budget evidence against another language.

## Ecosystem, support and deployment

Continued-support judgments rely on documented stewardship, source/license availability, maintenance and interoperability. They are qualitative signals, not audited staffing/runway, survival probabilities or perpetual support guarantees. A saved compiler archive can preserve a build today while failing to solve future OS/security maintenance. Older-generation BAML adoption is not proof that its newer general-purpose runtime is equally mature. Sponsor branding alone establishes no commercial commitment.

Compatibility receives lower decision weight under the final brief and concerns relevant current flagship targets. Older-OS/CPU probes provide deployment information, not a ranking reward. Actual target support still depends on the entire stack: language, libraries, UI/runtime, packaging, signing, updates and permissions. Cross-building is not target execution. Existing Rosetta or alternate local runtimes are not clean-device tests.

No clean Windows/Linux/phone deployment, native UI, browser rendering/accessibility, app-store installation, real network service, concurrency, HTTP p95/p99, GPU workload or battery test was performed. A JVM CLI result is not Android performance; a Swift CLI result is not SwiftUI performance; a Node worker is not an Electron app. Platform recommendations are engineering judgments, separately sourced from measurements.

## Publication and provenance

The public archive is a privacy-filtered export. Private paths/account identifiers are replaced by markers. Raw event transcripts, binary caches, credential material and unrelated instructions are omitted. Some historical diagnostics are excerpts rather than full logs. Historical checksums can refer to original local bytes; public transformed bytes need their own release manifest. Do not treat a redacted historical hash mismatch as numerical corruption without checking its provenance.

Archived scripts document the experiment and may retain unresolved path markers or historical layout assumptions. Publication-time adapters are new tools that must be verified separately. A new rerun must be labeled with its actual machine, versions, adapters, command and date; it must not overwrite the October observations. The source-graph completeness of experimental toolchains should be checked against the release's provenance manifest; readable Zero source projections alone do not necessarily reconstruct its authoritative graph.

This release is independent, AI-assisted research by Kian-hdr. It is not affiliated with or endorsed by language vendors, model vendors or the authors of cited methodological references. No peer review or independent human replication is asserted.

## Historical informal accuracy annotations

Some archived conversational reports retain an informal “Accuracy” footer. It is not a calibrated probability, statistical confidence level, external certification or substitute for the sample counts and limitations reported here. The maintained benchmark does not use that annotation to rank languages.
