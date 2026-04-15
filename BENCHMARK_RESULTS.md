# Benchmark Results

These are the real provider runs currently documented in this repository.
All recorded runs below were executed through the Codex CLI path, either with hosted Codex or with Codex pointed at local Ollama models.
The run directories themselves are local artifacts under `examples/*/runs/` and are gitignored.
This file is the checked-in summary of those runs.

Provider smoke results that are useful for implementation status, but are not benchmark-quality comparisons yet, are listed separately at the end of this file.

## `python_fixture_benchmark`

| Provider | Run ID | Best Objective | Improved | Duration (s) | Notes |
| --- | --- | ---: | :---: | ---: | --- |
| Hosted Codex | `hosted-codex-20260401` | `1.000` | yes | `153.231` | Solved in 1 proposal iteration. |
| Ollama `gpt-oss:20b` | `ollama-20b-20260401` | `0.050` | no | `240.149` | Proposal timed out at `240s`. |
| Ollama `gpt-oss:120b` | `ollama-120b-20260401` | `1.000` | yes | `274.820` | Solved in 1 proposal iteration. |

Winning runs changed the harness files:

- `AGENTS.md`
- `GEMINI.md`
- `scripts/bootstrap.sh`
- `scripts/test.sh`
- `scripts/validate.sh`

Local run directory names used for these runs:

- `examples/python_fixture_benchmark/runs/hosted-codex-20260401`
- `examples/python_fixture_benchmark/runs/ollama-20b-20260401`
- `examples/python_fixture_benchmark/runs/ollama-120b-20260401`

## `python_cli_benchmark`

| Provider | Run ID | Best Objective | Improved | Duration (s) | Notes |
| --- | --- | ---: | :---: | ---: | --- |
| Hosted Codex | `hosted-codex-20260401` | `1.000` | yes | `155.489` | Solved in 1 proposal iteration. |
| Ollama `gpt-oss:20b` | `ollama-20b-20260401` | `0.045` | no | `240.052` | Proposal timed out at `240s`. |

Winning hosted run changed the harness files:

- `AGENTS.md`
- `GEMINI.md`
- `scripts/bootstrap.sh`
- `scripts/test.sh`
- `scripts/validate.sh`

Local run directory names used for these runs:

- `examples/python_cli_benchmark/runs/hosted-codex-20260401`
- `examples/python_cli_benchmark/runs/ollama-20b-20260401`

## Takeaways

- The benchmark evidence documented in this repository is currently Codex-first. We have not documented an equivalent Claude Code or Opus result set here.
- There is no `metaharness` product blocker for hosted Codex. The important requirement is using `--hosted` when a project config defaults to local Ollama.
- On these benchmarks, hosted Codex was faster than local `gpt-oss:120b` and solved both tasks in a single proposal iteration.
- On these same runs, local `gpt-oss:20b` hit the configured `240s` proposal timeout on both benchmarks and did not improve the baseline.
- Reporting now filters transient workspace churn like `.venv/` and `__pycache__/` so summaries highlight actual harness edits rather than bootstrap side effects.

## Provider Smoke Results

These runs are useful for proving that a provider integration launches and produces inspectable artifacts.
They should not be treated as benchmark evidence on the same level as the Codex runs above.

### Gemini

| Target | Run ID | Outcome | Notes |
| --- | --- | --- | --- |
| `python_fixture_benchmark` | `gemini-smoke` | crash | Gemini launched, but `GEMINI_API_KEY` was not set in the environment |

Important observations:

- the Gemini backend is implemented and the CLI is callable through `metaharness`
- the current blocker is provider authentication, not parser or process integration
- there is still no successful real Gemini benchmark run recorded in this repository
