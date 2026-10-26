# Compatibility metadata correction

Reviewed 27 October 2026. The original metadata parser had a material bug: inside `LC_BUILD_VERSION`, it accepted both `minos` and nested linker/tool `version` as the deployment minimum. The latter overwrote the actual minimum with a linker version such as `27037.1`. `LC_VERSION_MIN_MACOSX` legitimately uses `version`, but it is a different command schema.

**Fixed only the metadata parser and derived metadata.** `parse_macho_load_commands` now accepts `minos` for modern load commands and `version` only for the legacy command. Original results are preserved at `deep_phase/compatibility/results_original.json`. Corrected `results.json` was regenerated solely from the already saved raw `.otool.txt` output; raw text was verified identical to each record's stdout. Eight metadata records changed. An independent comparison confirmed every field outside `deployment_load_commands` remained exactly unchanged. `metadata_correction.json` records changes and both result-file hashes.

No native tools, builds, runtime benchmarks or business implementations were rerun. Parser-only assertions passed for modern nested tool versions, legacy minimum-version commands and universal binaries with two slices.

| Produced artifact | Correct actual macOS deployment minimum | SDK metadata |
|---|---:|---:|
| Original Go | 13.0 | 26.2 |
| Original Swift | 27.2 | 27.0 |
| Original Zero | 27.0 | 27.0 |
| Original BAML | 11.0 | 26.5 |
| Original Rust | 11.0 | 27.0 |
| Original MoonBit | 27.0 | 27.0 |
| Swift explicit x86_64 variant | 13.0 | 27.0 |
| Swift explicit arm64 variant | 13.0 | 27.0 |
| Swift universal variant, both slices | 13.0 | 27.0 |

The Swift cross-build commands explicitly requested `x86_64-apple-macosx13.0` and `arm64-apple-macosx13.0`. Both builds succeeded, and raw `LC_BUILD_VERSION minos` confirms the requested 13.0 floor in both outputs and both universal slices. Thus the corrected metadata supports the claimed **build target**, while the original host-default Swift artifact actually targets 27.2.

Previously recorded runtime evidence is narrower: the original ARM worker and translated x86_64 variant each passed six smoke responses on this Mac; the arm64 macOS13 variant and universal package were build-only. No macOS13 system, physical Intel Mac, installer, signing/notarization or store workflow was tested. Metadata does not establish all linked dependency/API behavior on the declared minimum OS, nor prove public-device compatibility. The high host-default floors in original Swift/MoonBit/Zero artifacts are packaging/build-configuration findings, not intrinsic language minimum-OS requirements.
