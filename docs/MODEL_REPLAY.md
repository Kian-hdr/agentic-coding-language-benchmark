# Reproduction and model replay

## Three different claims

1. **Evidence verification:** check public file hashes, inspect source/counters and recompute summaries. No model call or candidate execution is needed.
2. **Software reproduction:** build archived generated source and run frozen requests on a new host/toolchain. This can validate behavior, but fresh performance is a new observation.
3. **Model re-authoring:** ask a currently accessible model to implement the same task again. This is a new experimental sample, not a deterministic replay of proprietary inference.

Do not use a successful step in one category to claim completion of another. CI verification does not rerun the original model, certify target devices or recreate historical timings.

## Publication-time commands

See the [software reproduction guide](REPRODUCTION.md) for current adapter syntax, toolchain requirements, preserved source gaps and output locations.

The entry points below are publication tooling, separate from the historical harness. Local preparation verified `verify.py --full` (946 export files, 42 fixtures, 3,946 oracle comparisons), `analyze.py --check`, all regenerated long-file hashes and seven focused unit tests. The portable Python adapter built and passed four final deep validation files/221 responses, pilot initial trial 1/69 checks and pilot extension trial 2/89 checks.

Other language adapters have not been revalidated in this public-release environment; the heavy compiler batch was deferred under host memory pressure. These checks establish the stated offline/data/Python behavior, not a fresh nine-language runtime comparison or model-authoring replication. See [toolchains](TOOLCHAINS.md) and [provenance](PROVENANCE.md). Run command help before expensive work.

```sh
python3 scripts/verify.py
python3 scripts/verify.py --full
python3 scripts/analyze.py --check
python3 scripts/datasets.py
python3 scripts/datasets.py --long
```

Normal datasets are frozen compressed synthetic fixtures. `--long` reconstructs larger transformed files with oracle expectations and can consume substantial disk space. Verify compressed and uncompressed hashes in their proper domains. Do not expect the old historical scripts to run unchanged with redacted path markers.

Deep software reproduction interface:

```sh
python3 scripts/reproduce.py build typescript --stage maintenance
python3 scripts/reproduce.py validate typescript --stage maintenance
python3 scripts/reproduce.py perf typescript --stage maintenance
```

Supported stage names are initial, optimized and maintenance. The publication adapter also provides pilot build/validation selection through `--phase pilot`, initial/extension stage and trial 1/2; consult its current help for argument syntax. Do not assume a pilot performance adapter or automatic model replay exists merely because historical scripts are archived.

Required language toolchains/dependencies must be installed separately. Record their exact versions; a compatible publication adapter is not a promise that old installers still work or that every modern compiler accepts unchanged experimental syntax. Build time remains separate from worker runtime. Any path/runtime adapter belongs outside archived source and must not silently repair business logic. Preserve observed failures as results. Use separate rerun output paths and never overwrite the historical records.

## Historical authoring configuration

The pilot runner records `codex exec`, model alias `gpt-6.1-sol`, medium reasoning, ephemeral mode, ignored user config, workspace-write sandbox selection and disabled named integrations, with usage JSON output. The deep runner imports the same configuration. Exact flags and prompts are archived in [pilot runner](../archive/pilot/scripts/benchmark_runner.py), [deep runner](../archive/deep/scripts/agent_runs.py), [pilot prompts](../archive/pilot/prompts/) and [deep prompts](../archive/deep/prompts/).

Those flags record intended controls, **not proof that the complete instruction/tool environment was empty or identical across turns**. Startup warnings, provider behavior, global instructions and account/tool context may have influenced input. The public package includes task prompts/packets and source/metrics, but omits private global AGENTS instructions, full hidden system context, account settings and raw agent event transcripts. It cannot reconstruct the exact total prompt or prove all private-context influences were removed historically.

The model alias was available to the original session. No repository claim guarantees that another account can access it now, that a similarly named product maps to the same backend, or that the backend remains unchanged. Model weights, inference seeds and service routing are not controlled public artifacts. No claim is made that language vendors trained or optimized GPT-6.1 Sol for their syntax.

## A defensible new authoring experiment

Model calls should be a separate explicit opt-in using the reader's own credentials and budget. They must not run automatically in ordinary verification or CI. Before new calls:

- Specify the actually accessible model identifier, provider, client version, reasoning/sampling settings, budgets and full instruction sources that can be disclosed.
- Use new independent workspaces and preserve the exact prompts, language packets, dependencies and tool permissions. Stage toolchains before timing.
- Freeze new holdouts outside agent workspaces; existing public cases can no longer serve as undisclosed tests.
- Record retries, turn timeouts, missing receipts, compiler failures and every eligible implementation rather than reporting only successes.
- Keep authoring, building, runtime measurement and qualitative ecosystem evaluation separate. Use more independent starts and task families before estimating general agent-language reliability.

Historical main design: two pilot starts per language (36 turns), then one deep application per language with three stages (27 turns). A replay should preserve or explicitly change this design rather than presenting a single quick implementation as a complete reproduction. The extra NumPy prompt is supplementary and receives no equal-budget ranking credit.

## What a fresh result can establish

A new host passing frozen tests supports implementation portability on that tested configuration. A fresh model producing good source supports that model/toolchain/task combination. Neither retroactively changes the October 2026 observations. Publish reruns with distinct dates, hardware, compiler/runtime versions, adapter revisions and limitations. Peer review or independent human replication requires actual external evidence, not another AI-assisted review inside this repository.
