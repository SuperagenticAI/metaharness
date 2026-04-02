# Experiments

This page records the experiments completed so far during development.

For repeated benchmark runs, use `metaharness experiment` so the results are saved as both JSON and TSV.

The experiment workflow is also influenced by [Autoresearch](https://github.com/karpathy/autoresearch) by Andrej Karpathy, especially in the emphasis on explicit experiment records, repeatable runs, and outcome-driven iteration.

## Early Scaffold Experiments

These were the first live local OSS checks used to validate the outer loop before the real benchmark targets were added.

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

- the local OSS path remained viable on a slightly richer scaffold with bootstrap and test scripts

## Real Benchmark Experiments

### `python_fixture_benchmark`

| Provider | Run ID | Best Objective | Improved | Duration (s) | Notes |
| --- | --- | ---: | :---: | ---: | --- |
| Hosted Codex | `hosted-codex-20260401` | `1.000` | yes | `153.231` | solved in 1 proposal iteration |
| Ollama `gpt-oss:20b` | `ollama-20b-20260401` | `0.050` | no | `240.149` | proposal timed out at `240s` |
| Ollama `gpt-oss:120b` | `ollama-120b-20260401` | `1.000` | yes | `274.820` | solved in 1 proposal iteration |

Winning hosted run changed:

- `AGENTS.md`
- `GEMINI.md`
- `scripts/bootstrap.sh`
- `scripts/test.sh`
- `scripts/validate.sh`

Observed quality:

- hosted Codex wrote stronger repository guidance and explicitly pointed the agent at `.metaharness` feedback
- local `gpt-oss:120b` solved the benchmark too, but with simpler script changes and slower turnaround
- local `gpt-oss:20b` did not improve the baseline within the configured timeout

### `python_cli_benchmark`

| Provider | Run ID | Best Objective | Improved | Duration (s) | Notes |
| --- | --- | ---: | :---: | ---: | --- |
| Hosted Codex | `hosted-codex-20260401` | `1.000` | yes | `155.489` | solved in 1 proposal iteration |
| Ollama `gpt-oss:20b` | `ollama-20b-20260401` | `0.045` | no | `240.052` | proposal timed out at `240s` |

Winning hosted run changed:

- `AGENTS.md`
- `GEMINI.md`
- `scripts/bootstrap.sh`
- `scripts/test.sh`
- `scripts/validate.sh`

Observed quality:

- hosted Codex correctly completed the instruction and script set needed for both the unit test flow and the CLI smoke command
- local `gpt-oss:20b` again timed out before producing an improving candidate

## Overall Conclusions So Far

1. Hosted Codex is the strongest current path for the real benchmarks in this repository.
2. Local `gpt-oss:20b` is useful for small smoke checks, but it is not yet reliable enough for the current real benchmarks with the present timeout settings.
3. Local `gpt-oss:120b` is capable on at least one real benchmark, but it is slower than hosted Codex.
4. Reporting is now good enough to compare providers by score, duration, and changed harness files without getting buried in transient `.venv` churn.
