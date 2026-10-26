# Reproduction guide

The public repository is an evidence package and a set of **publication-time adapters**. The immutable original, path-redacted harnesses live in `archive/*/scripts/`; the portable commands below are newly written for publication. Their timings are new observations and must not overwrite or be conflated with historical timings.

## 1. Verify the recorded evidence without models or compilers

Requires Python 3.9+ and its standard library. Python 3.12 is used in the public CI matrix; the original generator/worker versions are documented separately.

```sh
git clone https://github.com/Kian-hdr/agentic-coding-language-benchmark.git
cd agentic-coding-language-benchmark
python3 scripts/verify.py --full
python3 scripts/analyze.py --check
python3 -m unittest discover -s tests -v
python3 scripts/check_public.py
```

Use `python` instead of `python3` where appropriate. These checks verify export and fixture hashes, original scored-result completeness, known exclusions, numeric summaries, and recomputed expected responses. They do **not** independently repeat the model's authoring decisions, certify all candidate logic, or establish that recorded timing measurements happened on your machine.

The archive contains all 36 scored pilot case reports, 81 main deep build/validation/performance reports, 63 main agent-turn metric records and prompt files, long-run observations, supplementary NumPy records, and compatibility/correction records. Some records contain repeated observations of the same cases. See the [data dictionary](DATA_DICTIONARY.md).

## 2. Recover exact synthetic inputs

```sh
python3 scripts/datasets.py
```

This unpacks 42 deterministic gzip files under `.work/data/` and checks both compressed and uncompressed SHA-256 hashes. The compressed files preserve the exact original fixture bytes; random-number-generator changes cannot silently change them. Approximately 67.3 MiB of base fixtures are materialized (inspect `data/fixtures.json` for exact byte counts).

```sh
python3 scripts/datasets.py --long
```

The second command regenerates the eight-block final datasets and their expected outputs from frozen large inputs and the published oracle. It checks every resulting input/output hash against the original manifest. Allow roughly another 460 MiB of disk and meaningful CPU time. Existing matching files are reused; mismatching/partial files fail explicitly. Nothing overwrites `archive/`.

The historical random generator is also published as `lib/oracle.py` and `archive/deep/scripts/oracle.py`. `lib/oracle.py` retains its original `ROOT` convention and standalone main, so do not invoke it as a fixture installer. Import its pure functions or use the safe scripts above. The portable long generator replicates the original transformations and verifies hashes rather than pretending the original completion-marker-dependent orchestrator is portable.

## 3. Rebuild and validate a submitted implementation

On POSIX (macOS/Linux), Python requires no additional package:

```sh
python3 scripts/reproduce.py build python
python3 scripts/reproduce.py validate python
```

The default is the deep phase's final `maintenance` source. It validates all four final files (221 responses) and writes **new**, separate results under `.work/deep/python_1/maintenance/new_results/`. It does not rerun the language model.

Other examples after installing the [toolchains](TOOLCHAINS.md):

```sh
python3 scripts/reproduce.py build go
python3 scripts/reproduce.py validate go
python3 scripts/reproduce.py build typescript --stage initial
python3 scripts/reproduce.py validate typescript --stage initial
python3 scripts/reproduce.py build rust --stage maintenance
python3 scripts/reproduce.py validate rust --stage maintenance
```

Supported language names are `python`, `typescript`, `go`, `rust`, `swift`, `kotlin`, `moonbit`, `baml`, `zero`, and supplementary `python_numpy`. Dependency/toolchain absence and known canonical-source gaps fail explicitly. An adapter's existence is not proof of cross-platform build success; consult the publication verification record and original compatibility evidence. Native build commands and runtime versions are recorded locally in each `publication_build.json`.

Python's publication adapter executes the authored source with `-O`, after syntax compilation, rather than distributing host-version-specific `.pyc` files. It preserves business logic but is not a byte-identical replay of the original launcher. Other adapters replace host paths/configuration and excluded dependency caches; source snapshots remain unchanged.

### Pilot snapshots

Pilot initial and extension snapshots are distinct. Validate the stage you built, rather than accidentally testing final code against an initial score:

```sh
python3 scripts/reproduce.py build python --phase pilot --stage initial --trial 1
python3 scripts/reproduce.py validate python --phase pilot --stage initial --trial 1
python3 scripts/reproduce.py build python --phase pilot --stage extension --trial 2
python3 scripts/reproduce.py validate python --phase pilot --stage extension --trial 2
```

The pilot adapter replays correctness. Historical launcher and prepared-process performance are preserved in the archive, but pilot performance is not yet generalized into the new portable CLI. Different argument protocols are handled by the adapter. Historical initial/optimized Zero canonical graph availability and dependency-lock gaps are described in [provenance](PROVENANCE.md); never silently replace an initial snapshot with final code.

## 4. Run new component measurements

```sh
python3 scripts/reproduce.py perf python --repetitions 5
python3 scripts/reproduce.py perf python --long --repetitions 2 --timeout 120
```

These reuse the published resource/checker code, one worker per file. They do not recreate the original global randomized multi-language schedule: do not directly interpret a sequential local rerun as a controlled pairwise language comparison. Use dedicated hardware, matching versions and declared runtime settings if extending the study. Record all failures, exclusions, OS/CPU, dependencies, warm-up, background load and the schedule. Do not subtract startup or derive per-request p99 from batch wall time.

POSIX execution relies on `wait4`, process groups and `fcntl`. Offline data verification/analysis is portable, but a Windows execution backend has not been implemented. Successful Linux/macOS CI smoke checks are separate from the historical single-Mac measurements.

## 5. Rerun authoring separately

See [model replay](MODEL_REPLAY.md). The recorded `gpt-6.1-sol` alias, model access, private runtime instructions and exact original service state cannot be guaranteed for all readers. Hosted-model reproduction is stochastic and may cost money. No model call, credential setup or provider purchase runs automatically in this repository or CI.

## Checksums and changes

`archive/export_manifest.json` maps original file hashes to exported hashes and records path redaction. Historical hashes inside raw result records refer to original pre-redaction files and are intentionally retained; they need not equal sanitized public-source hashes. The export manifest is the integrity contract for published archive bytes. Derived CSV/JSON/Markdown can be regenerated with `python3 scripts/analyze.py` and checked with `--check`. A checksum provides integrity and internal consistency, not an external timestamp, independent replication or proof of an unobserved event.

## Text encoding

Maintained analysis and document checks explicitly read UTF-8. The first Windows CI run caught locale-dependent Markdown decoding; the fix changes publication tooling only, not any historical numeric observation. Generated numeric tables use UTF-8 text and the repository enforces LF checkout for text.
