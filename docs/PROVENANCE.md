# Provenance, disclosure and archive boundaries

## Ownership and roles

This is independent research published by **Kian-hdr**, at the maintainer's explicit request. Codex was used both to author the candidate programs and to build/review the evaluation and public package. The benchmark subject is the **software-authoring workflow**, not just a compiler's theoretical speed. AI-assisted reviewers were checks within the same project; they are not independent human replication or peer review.

No institutional affiliation, commercial support agreement, research funding declaration or external registration is asserted. This repository is a descriptive evidence release, not a journal submission. The maintainer authorized the public repository and independent-research attribution.

## Original versus publication-time materials

- `archive/` contains selected historical study materials, with private host paths in text replaced by symbolic `{ORIGINAL_*}` labels. Canonical Zero binary source graphs are retained byte-for-byte, with separate readable views. Numeric outcomes, timing fields, status flags, sample identifiers and missing usage were retained.
- `archive/export_manifest.json` records original SHA-256, exported SHA-256, original study-relative location, public location and whether redaction changed bytes. These hashes are integrity/provenance aids, not external time attestations.
- `scripts/`, `lib/`, `tests/`, maintained `docs/`, `results/` and CI are publication-time additions. Imported oracle/measurement code preserves the historical functions; the new build adapters change path/configuration plumbing and must not be represented as original launchers.
- Original generated business logic is not silently repaired for publication. Missing metadata and known defects remain visible. New local/CI correctness checks are reported separately from historical observations.
- Historical report links refer to the original directory layout; use the maintained README/docs and archive layout for public navigation. Symbolic host paths in historical scripts are intentional and do not execute as installation recipes.

## Included evidence

The package includes all36 scored pilot case reports (2,844 passed case observations, with repeated regression cases), pilot runtime/prepared/sorting follow-ups, all81 main deep build/validation/performance reports, main63 agent-turn metric records/prompts, phase source snapshots where available, long-run54 scheduled records, supplementary NumPy results/source, compatibility records and the metadata correction history. Language packets, specifications, locally written protocol and AI-assisted audit notes are retained. Source snapshots also contain authored tests and feedback where the original archive captured them.

All42 non-long synthetic JSONL input/expected fixtures are committed as deterministic gzip, with compressed and uncompressed hashes. Larger final fixtures are regenerated from the frozen inputs and oracle, then checked against all original input/expected hashes. No production/customer data is used. Individual successful timed-run output payloads are not all duplicated in Git; expected outputs, checker observations and retained hashes allow verification/reruns. Some successful long-run payloads were intentionally deleted after checking in the original experiment; the original measurement record says so.

## Explicit source-archive gaps

The original deep snapshot copier accepted a suffix allowlist that omitted `.graph` and `.lock`. Consequently:

1. **Pilot Zero:** all four canonical `zero.graph` files survive in the original pilot snapshots and are now exported, alongside their `.0` projections.
2. **Deep Zero:** the final current canonical graph is exported under the maintenance source snapshot. The historical initial and optimized canonical graphs were not preserved by that copier. Their text projections remain available, but they must not be presented as byte-identical canonical graph archives. The portable builder refuses a graph-less snapshot.
3. **Deep Rust:** the final current `Cargo.lock` is included with final maintenance source. Initial/optimized deep lock files were omitted by the original copier. Cargo manifests still pin direct dependency versions; recreating transitive resolution later does not prove the original lock state. Do not use the final lock as falsely labeled initial evidence.
4. **Model runtime context:** user prompts, packets, intended CLI flags and scalar usage receipts are published, but exact private/global/system instruction state and hosted service backend are not reconstructed. The historical model alias is not guaranteed to be available to every reader.

These limitations were identified during publication audit. They change the scope of reproducibility, not recorded test outcomes. A future independent rerun should publish immutable canonical sources, dependency locks and complete declared environment metadata at each stage.

## Deliberately excluded

Raw private agent event transcripts, hidden reasoning, global/user instruction files, account/session identifiers, credentials, unrelated project context, process-control/runtime state, compiler binaries, package caches and third-party vendor trees are excluded. Raw agent transcripts are not needed to recompute the numeric tables, but their absence limits independent reconstruction of every tool action and hidden-context influence.

Host-path substitutions are documented rather than silently treating original-file hashes as hashes of exported bytes. Timing/status fields are not normalized to flatter a candidate. Four timed-out deep optimization turns have no final usage receipt; their consumption is **unknown**, not zero. Correct-output runs with unsupported process-tree accounting retain correctness evidence but lose resource-ranking credit. Zero's partial final correctness remains an eligibility failure.

## Licensing and attribution

Original benchmark code, publication tooling, documentation and synthetic fixtures are distributed under the repository's MIT license, except any explicitly identified upstream material or existing file-specific terms. Compiler/runtime/SDK/package dependencies are not relicensed by this repository. They must be obtained separately under upstream terms; no entitlement to redistribute a compiler is inferred from generated-program rights. See `THIRD_PARTY_NOTICES.md` at repository root and version-local toolchain notes.

The language implementations were generated using Codex under this experiment's prompts. Publishing them demonstrates what was produced; it is not a claim to have invented the languages, their standard libraries, referenced algorithms, or upstream tooling. Methodological skills and source documentation are credited in [sources](SOURCES.md). No endorsement by model or language vendors is asserted.

### Canonical binary source graphs

Five available Zero `zero.graph` files are serialized source graphs, not compiler executables, and are included with their original byte hashes. Adjacent `.graph.txt` files are readable publication-time exports. An attempted text/binary roundtrip did not preserve identical bytes or text; therefore the text view is not substituted for canonical evidence. The failed roundtrip checks remain in `results/graph_roundtrip.json`. The native tool produced the views locally; source graphs were inspected through those views and generic byte checks before publication. No claim of a lossless text conversion is made.
