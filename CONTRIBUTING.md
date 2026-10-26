# Contributing and independent replication

Reports of errors, independent reruns and additional workloads are welcome. Please include the repository commit, OS/CPU/runtime versions, toolchain/dependency locks, exact commands, dataset hashes and complete status/output records. State whether you reanalyzed existing data, rebuilt candidate software, or re-authored it with a model. Do not call these the same experiment.

Keep original observations immutable. New timings belong in a separately labeled directory with provenance, scheduling, repetitions and exclusions. Preserve failures and absent receipts; never turn missing data into zero. A new model, runtime, compiler, task or implementation is an extension, not an exact replication by default.

Before a change, run `python3 scripts/verify.py --full`, `python3 scripts/analyze.py --check` and `python3 -m unittest discover -s tests -v`. Do not submit credentials, private machine paths, proprietary datasets, hidden model reasoning or raw account/runtime transcripts. Document necessary redactions. Changes to the analysis or oracle need a meaningful regression case and explanation of which conclusions change.

No automatic model calls run in CI. Please discuss expensive additional experiments before assuming maintainer-funded compute or model access.

## License for contributions

Original project code, research write-ups and synthetic data are MIT-licensed; see [licensing scope](LICENSING.md). Submit contributions under the same MIT terms unless different terms are explicitly identified and agreed before inclusion. Only contribute material you have the right to share, and retain necessary upstream attribution. External results should be proposed through a pull request with their full measurement provenance; contributors do not need direct write access to the main repository.
