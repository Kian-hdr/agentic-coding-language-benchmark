# Sources and attribution

This is independent, AI-assisted research by Kian-hdr. Source links support specific technical and stewardship statements; they are not endorsements of the benchmark or guarantees of future support. Official documentation establishes documented capabilities, not that this project executed every platform/API. Research was conducted October 26–27, 2026; live pages can change after that date. Historical versions and observed outputs take precedence when interpreting measurements.

## Primary experimental evidence

- [Pilot task and budget specification](../archive/pilot/reports/BENCHMARK.md), [historical runner](../archive/pilot/scripts/benchmark_runner.py), [source snapshots](../archive/pilot/sources/), [per-turn metrics](../archive/pilot/metrics/), [external results](../archive/pilot/results/).
- [Deep task specification](../archive/deep/reports/SPEC.md), [local protocol](../archive/deep/reports/PROTOCOL.md), [authoring runner](../archive/deep/scripts/agent_runs.py), [measurement source](../archive/deep/scripts/measure.py), [oracle](../archive/deep/scripts/oracle.py), [final longer-pass source](../archive/deep/scripts/long_run.py).
- [Deep stage snapshots](../archive/deep/sources/), [prompts](../archive/deep/prompts/), [metrics](../archive/deep/metrics/), [raw measurements](../archive/deep/results/), [compatibility records](../archive/deep/compatibility/).
- [Frozen fixture manifest](../data/fixtures.json), [dataset index](../data/index.json), [long-file metadata](../data/long_manifest.json).
- [Dated toolchain notes](../archive/toolchain_notes/) and [AI-assisted review notes](../archive/reviews/). These reviews belong to the same project, not independent human replications.

The archived scripts/reports are historical evidence with redacted paths and some omitted private material. Publication adapters, public manifests and later reruns form a different provenance layer. See [data dictionary](DATA_DICTIONARY.md) and [replay boundaries](MODEL_REPLAY.md).

## Language/runtime documentation and continued-support signals

| Language | Primary sources | Supported interpretation |
|---|---|---|
| Python | [PSF purpose/stewardship](https://www.python.org/psf/about/), [release downloads](https://www.python.org/downloads/), [Python documentation](https://docs.python.org/3/) | Established stewardship and documented runtime/library surface; release support is version-specific |
| TypeScript | [Microsoft compiler source](https://github.com/microsoft/TypeScript), [handbook](https://www.typescriptlang.org/docs/handbook/intro.html), [Node documentation](https://nodejs.org/docs/latest/api/) | Public compiler and JavaScript/Node ecosystem; static types do not automatically validate external runtime data |
| Go | [Go 1 compatibility policy](https://go.dev/doc/go1compat), [toolchain/target documentation](https://go.dev/doc/install/source), [standard library](https://pkg.go.dev/std) | Explicit compatibility aims and deployment routes, with policy exceptions; no perpetual-support promise |
| Rust | [project governance](https://rust-lang.org/governance/), [Rust Foundation](https://rustfoundation.org/about/), [target support tiers](https://doc.rust-lang.org/rustc/platform-support.html) | Public project governance and institutional support; compiler target tiers do not certify application dependencies or packaging |
| Swift | [project and governance](https://www.swift.org/about/), [platform support](https://www.swift.org/platform-support/), [compiler source](https://github.com/swiftlang/swift) | Open project/platform pathways; SwiftUI and other Apple frameworks are separate from language compiler availability |
| Kotlin | [FAQ](https://kotlinlang.org/docs/faq.html), [foundation structure](https://kotlinfoundation.org/structure/), [command-line compiler](https://kotlinlang.org/docs/command-line.html), [native targets](https://kotlinlang.org/docs/native-target-support.html) | JetBrains-led engineering, multi-organization governance and JVM/native routes; a JVM JAR is not an Android package |
| MoonBit | [language documentation](https://docs.moonbitlang.com/en/latest/), [compiler source/license](https://github.com/moonbitlang/moonbit-compiler), [core](https://github.com/moonbitlang/core), [build system](https://github.com/moonbitlang/moon), [official async IO](https://github.com/moonbitlang/async), [skills](https://github.com/moonbitlang/skills) | Substantial compiler/build/core/backend tooling and agent documentation; inspected compiler source lag/license terms and experimental IO affect independent-maintenance risk |
| BAML | [current language repository](https://github.com/BoundaryML/baml), [pinned 0.23.0 release](https://github.com/BoundaryML/baml/releases/tag/baml-language-0.23.0), [quickstart](https://boundaryml.com/quickstart), [team](https://boundaryml.com/who-are-we), [YC company listing](https://www.ycombinator.com/companies/boundary) | Current general-purpose language, real toolchain and team activity; older prompt-DSL uptake is not maturity evidence for every new language feature |
| Zerolang | [official Vercel Labs repository](https://github.com/vercel-labs/zerolang), [upstream agent evaluations](https://github.com/vercel-labs/zerolang/blob/main/evals/README.md) | Real experimental compiler/tooling and agent workflows; sponsor branding does not establish commercial support or production readiness |

These institutional/release signals support qualitative maintenance judgments. They do not establish audited staffing, future financial runway or numeric probabilities that a language will survive. Custom compiler terms should be read directly; this report does not substitute for legal review or claim user applications automatically inherit compiler licensing.

## Libraries and IO dependencies

- [serde_json](https://github.com/serde-rs/json): Rust JSON infrastructure used in the experiment; staged before authoring and disclosed separately from task business logic.
- [JSON-java / org.json](https://github.com/stleary/JSON-java): Kotlin/JVM JSON infrastructure; version and provenance recorded in the toolchain notes.
- [MoonBit async](https://github.com/moonbitlang/async): official native streaming IO and HTTP facilities, with experimental-status caveat. Local file-worker use does not establish a full HTTP benchmark.
- [NumPy documentation](https://numpy.org/doc/stable/user/whatisnumpy.html): compiled array operations relevant to the supplementary Python path. The extra NumPy prompt/dependency is not part of the equal-budget ranking.
- [OpenAI Codex source](https://github.com/openai/codex): general client reference. Historical flags, model alias and local access are established by the archived runner/metrics, not a promise that current public client/model access matches the historical environment.

## Methodological reference

Timothy Kassis, Vinayak Agarwal, Yuhuan He, Darshil Patel, and Aubrey M. Brueckner (2026). **Scientific Agent Skills: A Library of Procedural Knowledge for Research Agents.** arXiv:2609.00065, version 2 revised September 2, 2026. [arXiv record](https://arxiv.org/abs/2609.00065), [DOI: 10.48550/arXiv.2609.00065](https://doi.org/10.48550/arXiv.2609.00065).

The paper is cited as a methodological reference about explicit, inspectable research procedures and evidence boundaries. It is not a source for these language-performance numbers. Its authors did not review, endorse or independently replicate this benchmark. Its existence does not establish that this local protocol was externally preregistered or validated. Bibliographic details were checked against the arXiv record during publication preparation.

```bibtex
@misc{kassis2026scientificagentskills,
  title = {Scientific Agent Skills: A Library of Procedural Knowledge for Research Agents},
  author = {Kassis, Timothy and Agarwal, Vinayak and He, Yuhuan and Patel, Darshil and Brueckner, Aubrey M.},
  year = {2026},
  eprint = {2609.00065},
  archivePrefix = {arXiv},
  primaryClass = {cs.CL},
  doi = {10.48550/arXiv.2609.00065},
  url = {https://arxiv.org/abs/2609.00065}
}
```

## How to cite this repository

Until a versioned release/DOI exists, cite the repository owner, title, exact commit hash or release tag, experiment dates and access date. Do not invent a DOI, journal venue, peer-review status or institutional affiliation. A future independently executed rerun should cite both the archived experiment and its own new environment/results.
