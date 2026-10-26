# Open-source licensing and reuse

The original materials in this repository are released under the **MIT license** in [LICENSE](LICENSE), unless a file explicitly identifies different upstream terms. This is an open research project: you are welcome to inspect, run, copy, modify, extend and redistribute the materials, including for commercial use, under the MIT license's conditions.

## What the license covers

| Original project material | License |
|---|---|
| Benchmark harnesses, portable adapters, analysis scripts and tests | MIT |
| Model-authored candidate implementations, to the extent rights are held by the project, subject to any identified file-specific terms | MIT |
| Research reports, study write-up, methods, findings and limitations | MIT |
| README, documentation, reusable AGENTS.md policy and setup prompt | MIT |
| Synthetic inputs, expected outputs, measured results and derived tables | MIT |
| Original native diagrams, chart definitions and visual data | MIT |

The study write-up is openly reusable along with the software and data. The current release is an exploratory research report and benchmark; a later peer-reviewed paper would be a separate publication. Any separately published paper will state its applicable license explicitly, and existing MIT permissions for repository material remain available.

## Your permissions and responsibilities

You may run the benchmark on your own machine, test other models or workloads, create forks, build upon the results and share improvements. Keep the copyright and permission notice when distributing copies or substantial portions of MIT-licensed material. The project is provided without warranty; the full terms in [LICENSE](LICENSE) control.

For scholarly reuse, please cite the release or commit you used using [CITATION.cff](CITATION.cff). Citation is a research practice; it does not replace the MIT notice requirement.

## Third-party boundaries

We cannot relicense someone else's compiler, SDK, model weights, package or quoted/reference material. Their own licenses and access terms apply. They are not made open source merely because this benchmark references or measures them. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) and [provenance](docs/PROVENANCE.md). The public repository excludes credentials, private runtime context, compiler executables and third-party dependency caches.

## Contribute openly

Please use issues for questions or findings, and pull requests for changes and additional result records. Include the hardware, OS, model/runtime/toolchain versions, dataset hashes, exact commands and complete success/failure/exclusion records. Keep new measurements separate from immutable historical observations. [CONTRIBUTING.md](CONTRIBUTING.md) explains the evidence requirements.
