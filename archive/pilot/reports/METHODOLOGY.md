# Scope and interpretation

This evaluation tests software authored by an actual Codex CLI invocation of
`gpt-6.1-sol`, with medium reasoning, on this Mac. It does not test models called
by the resulting programs. Every task is deterministic and has no model API
dependency. Model availability was independently smoke-tested before trials.

## Comparison

Nine languages, two independently started programs per language, each followed
by a fresh agent turn adding an operation to its existing source. All receive
identical task semantics and a short, neutral language-specific toolchain packet.
Agents may inspect that toolchain's local help/standard library. Model versions,
reasoning, CLI flags and time limits remain fixed. Source, prompts, tool events,
compiler versions and independent evaluator results are preserved.

69 initial external test cases cover a deduplicating financial-style ledger,
lexically ordered topological sorting, expression parsing, and unknown-operation
handling. The later change adds interval merging. Its 89 external cases include
all 69 prior cases plus 20 new cases. Thus 316 checks per language across two
trials are repeated observations, not 316 independent software projects.

The evaluator is outside each run's folder and never included in model prompts.
Agents were instructed not to inspect other runs or evaluation files. A separate
source/log review checked both trials' completed programs for obvious answer
hardcoding, other-language computation, and cross-run access. This is an honest
agent experiment, not a sandbox security evaluation or contamination-proof test.

## Deliberate boundaries

- Native/macOS command-line business logic only. No mobile UI, SwiftUI, Android,
  full-stack website, GPU kernel, databases, production deployment or large-repo
  maintenance workload was tested.
- Short deadlines measure bounded usefulness, not eventual possibility.
- Correctness includes an independent oracle and edge cases; all inputs conform
  to the specified schema. This is not exhaustive proof or a security audit.
- All substantive computation stays in the target language. Wrappers can transport
  input and launch or compile code. Rust's pinned serde_json and Kotlin's pinned
  org.json are disclosed JSON-protocol exceptions; dependency setup is outside
  the coding timer.
- Both fresh and cached input tokens and generated tokens are retained. Token
  totals are not dollar costs or account-percentage estimates.
- Authoring wall time includes agent/tool latency and local checks. Some sessions
  run concurrently, so differences can reflect API queueing or host contention.
  Do not infer language-intrinsic speed from this number.
- Separate sequential process tests measure end-to-end `run.sh` behavior after
  authoring. Some generated launchers recheck/rebuild. These times include their
  actual startup/build overhead and are not isolated algorithm throughput.
- A second, prepared-executable comparison removes wrapper/rebuild overhead,
  packs BAML, and uses release builds for Rust and MoonBit without changing
  business logic. It tests the 1,000-entry ledger, 100-node graph and 1,000
  intervals. File-versus-argv transport is retained; the 5,000-entry input is
  excluded from this comparison because command-line transport limits can
  confound a language comparison. Even prepared times include startup/JSON IO,
  and are not steady-state server or isolated algorithm throughput.
- Vendor-specific agents or token-level constrained decoders were not substituted
  for Codex. Findings apply to the exposed CLI and documented Codex-compatible
  workflow, not to every vendor's preferred harness.

## Adjustments preserved in the record

The user expanded the initial three-candidate/two-baseline comparison to all nine
languages before the additional trials. Python's initial 3.9 system-runtime smoke
was excluded because a supported 3.14 installation was already available. Its
scored runs both use Python 3.14.7; the preliminary run remains in `preliminary/`.
The initial comparison and all nine final packets are retained.

## Support and future viability

Continuation judgments are qualitative, based on documented governance, source
availability, release history, team breadth, compatibility commitments, and
interoperability/exit cost. They are not probabilities, audited staffing, verified
runway, or guarantees of future support. Employer and repository branding alone
does not establish these things. Published old-generation adoption does not prove
a replacement compiler is mature.

## Decision standard

Prefer correctness and preservation of existing behavior before speed. For an
existing long-lived codebase, require credible support and an economical exit
route in addition to a promising pilot. A small difference in two runs is not
enough to justify a language migration. The best language for a platform can
remain its native language even when another wins this command-line benchmark.
