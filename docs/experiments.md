# Experiments

This page is the full experiment registry for `metaharness` development so far.

It covers three kinds of work:

- real provider benchmark runs that shaped the current product position
- provider smoke runs that prove integrations launch and produce artifacts
- fake-backend validation runs that proved the framework and benchmark targets before spending model calls
- early development experiments that were run in temporary workspaces and are summarized here from development notes

Important artifact policy:

- run directories under `examples/*/runs/` are local artifacts and are gitignored
- this page and the top-level `BENCHMARK_RESULTS.md` file are the checked-in summaries of the important named runs
- anonymous temporary test runs created during unit tests are not listed here one by one

For repeated benchmark runs, use `metaharness experiment` so the results are saved as both JSON and TSV.

The experiment workflow is also influenced by [Autoresearch](https://github.com/karpathy/autoresearch) by Andrej Karpathy, especially in the emphasis on explicit experiment records, repeatable runs, and outcome-driven iteration.

## Experiment Registry

| Category | Target | Backend / Model | Baseline -> Best | Status | Notes |
| --- | --- | --- | ---: | --- | --- |
| Early development | `local-oss-smoke` scaffold | Codex over Ollama `gpt-oss:20b` | `0.200 -> 1.000` | historical | first successful local OSS scaffold run, temporary workspace only |
| Early development | `local-oss-medium` scaffold | Codex over Ollama `gpt-oss:20b` | `0.0625 -> 1.000` | historical | richer scaffold with bootstrap and test scripts, temporary workspace only |
| Framework validation | `ticket_router` `smoke` | fake backend | `0.750 -> 1.000` | local artifact | early end to end deterministic example run |
| Framework validation | `ticket_router` `fake-run` | fake backend | `0.750 -> 1.000` | local artifact | later regression run after outcome ledger changes |
| Real benchmark validation | `python_fixture_benchmark` `smoke-real-target` | fake backend | `0.050 -> 1.000` | local artifact | first real benchmark target proved end to end without live model calls |
| Real benchmark | `python_fixture_benchmark` `hosted-codex-20260401` | hosted Codex | `0.050 -> 1.000` | documented | solved in one proposal iteration |
| Real benchmark | `python_fixture_benchmark` `ollama-20b-20260401` | Codex over Ollama `gpt-oss:20b` | `0.050 -> 0.050` | documented | proposal timed out at `240s` |
| Real benchmark | `python_fixture_benchmark` `ollama-120b-20260401` | Codex over Ollama `gpt-oss:120b` | `0.050 -> 1.000` | documented | solved in one proposal iteration, slower than hosted Codex |
| Real benchmark | `python_cli_benchmark` `hosted-codex-20260401` | hosted Codex | `0.045 -> 1.000` | documented | solved in one proposal iteration |
| Real benchmark | `python_cli_benchmark` `ollama-20b-20260401` | Codex over Ollama `gpt-oss:20b` | `0.045 -> 0.045` | documented | proposal timed out at `240s` |
| Provider smoke | `python_fixture_benchmark` `gemini-smoke` | Gemini CLI | `0.050 -> crash` | documented | Gemini launched but failed because `GEMINI_API_KEY` was not set |
| Release validation | `python_fixture_benchmark` `ci-fixture-local-check` | fake backend | `0.050 -> 1.000` | local artifact | used to validate uv-first CI and CLI flow |
| Release validation | `python_cli_benchmark` `ci-cli-local-check` | fake backend | `0.045 -> 1.000` | local artifact | used to validate uv-first CI and CLI flow |

## Early Development Experiments

These runs happened before the real benchmark targets existed.
They were important because they proved that the outer loop, Codex integration, local Ollama path, and on-disk run structure all worked together.

### `local-oss-smoke`

Provider:

- Codex over Ollama
- model: `gpt-oss:20b`

Result:

- baseline objective: `0.200`
- best candidate objective: `1.000`

Winning changes:

- `AGENTS.md`
- `GEMINI.md`
- `scripts/validate.sh`

Main takeaway:

- the local OSS path worked end to end and could solve a small scaffold profile

Artifact note:

- this run was created in a temporary workspace during development and is not committed

### `local-oss-medium`

Provider:

- Codex over Ollama
- model: `gpt-oss:20b`

Result:

- baseline objective: `0.0625`
- best candidate objective: `1.000`

Winning changes:

- `AGENTS.md`
- `GEMINI.md`
- `scripts/bootstrap.sh`
- `scripts/validate.sh`
- `scripts/test.sh`

Main takeaway:

- the local OSS path remained viable on a richer scaffold with real bootstrap and test scripts

Artifact note:

- this run was created in a temporary workspace during development and is not committed

## Checked Local Validation Runs

These runs are important because they prove the framework and example targets work even without live provider calls.
Their directories are local artifacts under `examples/*/runs/` and are gitignored.

### `ticket_router`

Named local runs:

- `examples/ticket_router/runs/smoke`
- `examples/ticket_router/runs/fake-run`

Observed result:

- baseline objective: `0.750`
- best candidate objective: `1.000`

Why it matters:

- it is the smallest deterministic end to end example in the repository
- it proved the early engine and later served as a regression check after ledger changes

### `python_fixture_benchmark` `smoke-real-target`

Named local run:

- `examples/python_fixture_benchmark/runs/smoke-real-target`

Observed result:

- baseline objective: `0.050`
- best candidate objective: `1.000`

Why it matters:

- this was the first real coding-tool benchmark target
- it proved that the benchmark was no longer just a placeholder scaffold

### Release validation runs

Named local runs:

- `examples/python_fixture_benchmark/runs/ci-fixture-local-check`
- `examples/python_cli_benchmark/runs/ci-cli-local-check`

Observed result:

- both fake-backend runs reached `1.000`

Why they matter:

- they validated the uv-first release flow
- they mirrored the important fake smoke paths used in CI

## Real Provider Benchmark Experiments

All real provider runs documented here were executed through the Codex CLI path.
This is why the current public benchmark evidence for `metaharness` is Codex-first.

### `python_fixture_benchmark`

| Provider | Run ID | Best Objective | Improved | Duration (s) | Notes |
| --- | --- | ---: | :---: | ---: | --- |
| Hosted Codex | `hosted-codex-20260401` | `1.000` | yes | `153.231` | solved in 1 proposal iteration |
| Ollama `gpt-oss:20b` | `ollama-20b-20260401` | `0.050` | no | `240.149` | proposal timed out at `240s` |
| Ollama `gpt-oss:120b` | `ollama-120b-20260401` | `1.000` | yes | `274.820` | solved in 1 proposal iteration |

Winning harness changes:

- `AGENTS.md`
- `GEMINI.md`
- `scripts/bootstrap.sh`
- `scripts/test.sh`
- `scripts/validate.sh`

Observed quality:

- hosted Codex wrote stronger repository guidance and explicitly pointed the agent at `.metaharness` feedback
- local `gpt-oss:120b` solved the benchmark too, but with simpler script changes and slower turnaround
- local `gpt-oss:20b` did not improve the baseline within the configured timeout

Artifact note:

- the run summaries are documented in this repository
- the corresponding run directories are local artifacts and are not committed

### `python_cli_benchmark`

| Provider | Run ID | Best Objective | Improved | Duration (s) | Notes |
| --- | --- | ---: | :---: | ---: | --- |
| Hosted Codex | `hosted-codex-20260401` | `1.000` | yes | `155.489` | solved in 1 proposal iteration |
| Ollama `gpt-oss:20b` | `ollama-20b-20260401` | `0.045` | no | `240.052` | proposal timed out at `240s` |

Winning hosted harness changes:

- `AGENTS.md`
- `GEMINI.md`
- `scripts/bootstrap.sh`
- `scripts/test.sh`
- `scripts/validate.sh`

Observed quality:

- hosted Codex correctly completed the instruction and script set needed for both the unit test flow and the CLI smoke command
- local `gpt-oss:20b` again timed out before producing an improving candidate

Artifact note:

- the run summaries are documented in this repository
- the corresponding run directories are local artifacts and are not committed

## Provider Smoke Experiments

These runs are important because they prove a provider integration actually launches through `metaharness`, writes proposal artifacts, and can be inspected after the fact.
They are not yet benchmark-quality evidence unless the provider produces a meaningful candidate on a real target.

### `python_fixture_benchmark` with Gemini

| Provider | Run ID | Best Objective | Outcome | Notes |
| --- | --- | ---: | --- | --- |
| Gemini CLI | `gemini-smoke` | baseline only | crash | Gemini started but exited with `When using Gemini API, you must specify the GEMINI_API_KEY environment variable.` |

What this means:

- Gemini support is real in the library
- the current blocker is authentication in the runtime environment
- Gemini is not benchmark-validated yet in this repository

## What Is Still Missing

The registry is still incomplete in two meaningful ways:

1. There is no documented `python_cli_benchmark` run yet for local `gpt-oss:120b`.
2. There is no successful real Gemini benchmark run in this repository yet.
3. There is no documented Claude Code or Opus result set in this repository yet.

Those are the most obvious next experiments if the goal is to broaden the evidence base.

## Overall Conclusions So Far

1. Hosted Codex is the strongest current path for the real benchmarks in this repository.
2. Local `gpt-oss:20b` is useful for small smoke checks, but it is not yet reliable enough for the current real benchmarks with the present timeout settings.
3. Local `gpt-oss:120b` is capable on at least one real benchmark, but it is slower than hosted Codex.
4. Fake-backend validation runs were valuable because they let the framework, CLI, and benchmarks mature before burning live model time.
5. Reporting is now good enough to compare providers by score, duration, and changed harness files without getting buried in transient `.venv` churn.
