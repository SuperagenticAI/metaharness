# metaharness Benchmarks

`metaharness` ships benchmark targets for coding-agent harness optimization.

These are not prompt-only demos. Each benchmark is a small filesystem project with:

- `AGENTS.md`
- `GEMINI.md`
- real helper scripts under `scripts/`
- deterministic `tasks.json` checks
- optional held-out `test_tasks.json` checks
- a real fixture repo that the scripts exercise

## Benchmarks

### `python_fixture_benchmark`

Path: `examples/python_fixture_benchmark`

Focus:

- real `python -m venv` bootstrap
- real `unittest` run against a fixture package
- instruction-file safety and context checks
- paper-like frontier defaults with held-out test tasks

Run it:

```bash
uv run metaharness run examples/python_fixture_benchmark --backend fake --budget 1
uv run metaharness run examples/python_fixture_benchmark --backend codex --hosted --budget 3
uv run metaharness run examples/python_fixture_benchmark --backend codex --oss --local-provider ollama --model gpt-oss:120b --proposal-timeout 420 --budget 3
uv run metaharness experiment --config examples/experiment_configs/codex-paperlike-fixture.json
```

### `python_cli_benchmark`

Path: `examples/python_cli_benchmark`

Focus:

- real `python -m venv` bootstrap
- real `unittest` run against a CLI fixture package
- real CLI smoke command on fixture data
- instruction-file safety and context checks

Run it:

```bash
uv run metaharness run examples/python_cli_benchmark --backend fake --budget 1
uv run metaharness run examples/python_cli_benchmark --backend codex --hosted --budget 1
uv run metaharness run examples/python_cli_benchmark --backend codex --oss --local-provider ollama --model gpt-oss:20b --proposal-timeout 240 --budget 1
```

## Reporting

Summarize all runs for a project:

```bash
uv run metaharness summarize examples/python_fixture_benchmark
uv run metaharness summarize examples/python_cli_benchmark
```

Compare specific runs:

```bash
uv run metaharness compare \
  examples/python_fixture_benchmark/runs/hosted-codex-20260401 \
  examples/python_fixture_benchmark/runs/ollama-20b-20260401 \
  examples/python_fixture_benchmark/runs/ollama-120b-20260401
```

Notes:

- use `--hosted` when a benchmark config defaults to local Ollama but you want the hosted Codex provider
- reporting filters transient workspace churn such as `.venv/` and `__pycache__/` so run summaries emphasize actual harness edits
