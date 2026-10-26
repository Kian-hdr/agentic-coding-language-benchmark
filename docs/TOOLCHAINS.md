# Toolchains and dependencies

## Historical versions

These are the versions pinned or installed for the recorded October 26–27, 2026 experiment. Availability of an old download and behavior on another OS are separate questions. Do not silently substitute versions and label the result an exact replication.

| Language | Recorded compiler/runtime | Approved dependency/path |
|---|---|---|
| Python | CPython 3.14.7 | Standard library; separate extra-prompt NumPy 2.5.4 experiment |
| TypeScript | TypeScript 7.0.2, Node 26.0.0 | `@types/node` 26.6.5 |
| Go | Go 1.27.3 | Standard library |
| Rust | Rust 1.99.1 | `serde_json` 1.0.154; deep typed parser additionally `serde` 1.0.229; release Cargo metadata in snapshots |
| Swift | Swift 6.4, Xcode-provided compiler | Foundation/standard libraries |
| Kotlin | Kotlin 2.4.21, OpenJDK 21.0.12.1 | `org.json:json:20260814`; JVM target 21 |
| MoonBit | `moonc` 0.10.17, `moon` 0.1.20261023 | Deep native IO uses official `moonbitlang/async` 0.22.5 |
| BAML | General-purpose language 0.23.0, wrapper 0.2.5 | Native packaged runtime; distinguish from the older prompt DSL |
| Zerolang | 0.3.4 | Native backend, canonical graph plus text projection |

Version-local setup notes, source links and retained download hashes are in [`archive/toolchain_notes/`](../archive/toolchain_notes/). No compiler binary, SDK, package cache, third-party vendored source tree or authentication material is redistributed. Installing a toolchain does not establish a right to redistribute it; upstream licenses govern.

## Portable adapter configuration

The adapter uses commands on `PATH` by default. Optional local overrides belong in an ignored `toolchains.local.json` (copy `toolchains.example.json`). Values can be executable names or absolute paths on **your** machine. Never commit local paths or credentials.

Keys: `python`, `python_numpy`, `node`, `tsc`, `node_types`, `go`, `cargo`, `cargo_home`, `rustup_home`, `rust_vendor`, `swiftc`, `kotlinc`, `java`, `java_home`, `json_jar`, `moon`, `moon_home`, `moon_deps`, `baml`, `baml_home`, `zero`. `BENCH_<UPPERCASE_KEY>` can select an executable where supported by the CLI; configuration is explicit for dependency directories.

- **TypeScript:** install the pinned TypeScript and node declarations in a local directory. Set `tsc` to its executable and `node_types` to its `node_modules/@types` directory. For example: `npm install --prefix .toolchains/typescript --ignore-scripts typescript@7.0.2 @types/node@26.6.5`. Check package provenance before installation.
- **Rust:** install the required Rust toolchain. The adapter uses the archived Cargo manifest/lock when present. It can use a separately obtained vendored directory via `rust_vendor`, otherwise ordinary Cargo resolution may download dependencies. Missing historical lock files are provenance gaps, not silently supplied historical evidence.
- **Kotlin:** install Kotlin/JDK21 and obtain `org.json:json:20260814` from the official Maven artifact route. Set `json_jar`; set `java_home` if needed. The JAR is not an Android APK.
- **MoonBit:** use a version-matched installation and `MOON_HOME`/`moon_home`. The module declares async0.22.5. Without a local `moon_deps` cache the compiler may resolve/download declared packages; with `moon_deps` it builds frozen. The evaluated compiler/core snapshots are not interchangeable with arbitrary newer binaries.
- **BAML:** install wrapper0.2.5 with language0.23.0 from the upstream release. Set `baml_home` for the installation; the adapter sets `DO_NOT_TRACK=1`. Consult upstream telemetry documentation.
- **Zero:** install0.3.4. Native backend limitations and canonical graph archive gaps can prevent historical builds. These are reported rather than “fixed” in published candidate logic.
- **NumPy:** create a separate environment with NumPy2.5.4 and set `python_numpy` to that interpreter. This is supplementary and not an equal-budget tenth language.

The original archived shell wrappers contain symbolic `{ORIGINAL_*}` substitutions and are historical records, not runnable installation instructions. The public adapters build in `.work/` and never mutate `archive/`. Public CI does not download or execute every compiler.

## Hardware/environment disclosure

Original recorded execution platform: Apple Silicon, Darwin27.2.0, ARM64. A publication-time inspection of the same host reports AppleM5, 24GiB RAM and10 logical CPUs. The CPU/RAM inspection was **not recorded contemporaneously in every original run**, so it is supplementary environment identification rather than a per-run hardware attestation. No dedicated-machine, fixed-power, thermal isolation or energy measurement is claimed. Resource flags and observed background variability remain part of the interpretation.
