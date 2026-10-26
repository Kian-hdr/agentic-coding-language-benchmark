# Benchmark scope-compliance review

Read-only implementation/log audit performed 26 October 2026. Only this report was written; no benchmark implementation, output, or evaluator was changed or run during review.

## Finding

No apparent scope-compliance violations found in reviewed material. This is a static source/log review, not a forensic guarantee or a correctness assessment.

- All nine first trials were reviewed after completion, including their initial and extension command logs.
- All nine completed second trials were reviewed, including initial and extension command logs.
- Zero second trial was initially reviewed from its saved initial snapshot while its extension was active. After `extension_metrics.json` existed, its final source, wrapper and extension log were reviewed read-only, closing the last coverage gap. No apparent violation found.
- No observed cross-run source access, evaluator access, answer retrieval, or hidden-case access in the reviewed command logs. Absolute run paths encountered in Go/Kotlin logs referenced those agents' own workspaces. Shared compiler/runtime/library paths were expected infrastructure.
- Wrappers perform environment/path setup, building, raw file reading/argument forwarding, and execution only. Business algorithms remain in the designated language. Raw `cat` transport in MoonBit, Go, Rust and Zero wrappers is permitted by the protocol; it performs no business computation.
- No obvious hardcoded-answer behavior found in application code. Fixed operation/error names and normal algorithm constants are expected. Literal input/output examples are located in local tests. JSON libraries and Rust vendored packages are preinstalled infrastructure, not outsourced business logic.
- Kotlin and TypeScript executable artifacts were newer than their corresponding first-trial source at inspection. Swift and Rust first-trial artifacts were also newer. This limited timestamp check is not a byte-level source/binary identity proof.

## Inspected implementation routes

| Language | Business source | Wrapper |
|---|---|---|
| BAML | `runs/baml_{1,2}/baml_src/main.baml` | `runs/baml_{1,2}/run.sh` |
| MoonBit | `runs/moonbit_{1,2}/solution/solution.mbt` and `solution/cmd/main/main.mbt` | `runs/moonbit_{1,2}/run.sh` |
| Kotlin | `runs/kotlin_{1,2}/Main.kt` | `runs/kotlin_{1,2}/run.sh` |
| Swift | `runs/swift_{1,2}/main.swift` | `runs/swift_{1,2}/run.sh` |
| Rust | `runs/rust_{1,2}/src/main.rs` | `runs/rust_{1,2}/run.sh` |
| TypeScript | `runs/typescript_1/main.ts`; second trial `main.ts` and `operations.ts` | `runs/typescript_{1,2}/run.sh` |
| Python | `runs/python_{1,2}/main.py` | `runs/python_{1,2}/run.sh` |
| Go | `runs/go_{1,2}/main.go` | `runs/go_{1,2}/run.sh` |
| Zero | `runs/zero_1/src/{main,lib}.0`; `runs/zero_2/src/{main,lib}.0` (initial snapshot also inspected) | corresponding `run.sh` |

## Log coverage

Counts below are logged `command_execution` items, including start/completion records if both exist. They indicate reviewed log coverage, not a count of unique shell invocations.

| Run | Command records |
|---|---|
| baml_1 | initial: 18; extension: 10 |
| baml_2 | initial: 24; extension: 12 |
| go_1 | initial: 24; extension: 8 |
| go_2 | initial: 24; extension: 10 |
| kotlin_1 | initial: 10; extension: 12 |
| kotlin_2 | initial: 14; extension: 8 |
| moonbit_1 | initial: 18; extension: 10 |
| moonbit_2 | initial: 22; extension: 8 |
| python_1 | initial: 10; extension: 8 |
| python_2 | initial: 14; extension: 8 |
| rust_1 | initial: 12; extension: 8 |
| rust_2 | initial: 16; extension: 6 |
| swift_1 | initial: 18; extension: 8 |
| swift_2 | initial: 18; extension: 6 |
| typescript_1 | initial: 8; extension: 8 |
| typescript_2 | initial: 8; extension: 8 |
| zero_1 | initial: 58; extension: 8 |
| zero_2 | initial: 86; extension: 16 |

Total reviewed command records: 564. Both phases of all 18 runs are covered. Zero2 final extension review found only project-local graph patches, code/tests/documentation and toolchain commands; wrapper remained raw transport and execution.
