# CLI Reference

The `metaharness` CLI covers four workflows:

1. scaffold a project
2. run or probe a backend
3. inspect and export results
4. execute repeated experiment matrices

Show help:

```bash
uv run metaharness --help
```

Many reporting commands support:

- plain text output by default
- `--json` for machine-readable output
- `--tsv` for spreadsheet-friendly export where supported

## `scaffold`

Create a new coding-tool project:

```bash
uv run metaharness scaffold coding-tool ./my-coding-tool-optimizer
```

Profiles:

- `standard`
- `local-oss-smoke`
- `local-oss-medium`

<div class="command-grid" markdown="1">
<div class="command-card" markdown="1">
### Standard

Best default for a new project.

```bash
uv run metaharness scaffold coding-tool ./my-project
```
</div>
<div class="command-card" markdown="1">
### Fast Local Smoke

Smaller harness aimed at local OSS smoke runs.

```bash
uv run metaharness scaffold coding-tool ./my-local-oss-smoke --profile local-oss-smoke
```
</div>
<div class="command-card" markdown="1">
### Medium Local OSS

Restores bootstrap and test scripts while staying lighter than the full scaffold.

```bash
uv run metaharness scaffold coding-tool ./my-local-oss-medium --profile local-oss-medium
```
</div>
</div>

## `run`

Run one optimization project:

```bash
uv run metaharness run ./my-coding-tool-optimizer --backend fake --budget 1
```

Use this when you want a single benchmark or project run and care about the winning candidate, not aggregate trial statistics.

Important options:

- `--backend`
- `--budget`
- `--run-name`
- `--hosted`
- `--oss`
- `--local-provider`
- `--model`
- `--proposal-timeout`

<div class="command-grid" markdown="1">
<div class="command-card" markdown="1">
### Fake Backend

Best for smoke checks and development.

```bash
uv run metaharness run ./my-coding-tool-optimizer --backend fake --budget 1
```
</div>
<div class="command-card" markdown="1">
### Hosted Codex

Best current path for real benchmark quality.

```bash
uv run metaharness run ./my-coding-tool-optimizer --backend codex --hosted --budget 1
```
</div>
<div class="command-card" markdown="1">
### Local Codex Over Ollama

Local-only path for OSS model runs.

```bash
uv run metaharness run ./my-coding-tool-optimizer --backend codex --oss --local-provider ollama --model gpt-oss:20b --proposal-timeout 240 --budget 1
```
</div>
</div>

## `experiment`

Run a benchmark x backend x budget x trial matrix:

```bash
uv run metaharness experiment ./examples/python_fixture_benchmark --backend fake --trials 3
```

Use this when you want repeatable benchmark results instead of one-off runs.

<div class="command-grid" markdown="1">
<div class="command-card" markdown="1">
### Saved Config

The most reusable path for teams.

```bash
uv run metaharness experiment --config ./examples/experiment_configs/fake-benchmarks.json
```
</div>
<div class="command-card" markdown="1">
### Multiple Budgets

Compare how much improvement you get from a larger search budget.

```bash
uv run metaharness experiment ./examples/python_fixture_benchmark --backend fake --budget 1 --budget 2 --trials 2
```
</div>
<div class="command-card" markdown="1">
### TSV Export

Send aggregate results straight to a spreadsheet or notebook.

```bash
uv run metaharness experiment ./examples/python_fixture_benchmark --backend fake --trials 3 --tsv
```
</div>
</div>

This command writes:

- `experiment.json`
- `trials.json`
- `aggregates.json`
- `trials.tsv`
- `aggregates.tsv`

Config files can contain:

- `project_dirs`
- `backends`
- `budgets`
- `trial_count`
- `models`
- `results_dir`
- `backend_overrides`

If a config file is provided, relative paths are resolved from the config file location.
CLI flags override the corresponding config values.

## `smoke codex`

Probe the Codex path before spending model calls:

```bash
uv run metaharness smoke codex ./my-coding-tool-optimizer --probe-only
```

Probe the local Ollama path:

```bash
uv run metaharness smoke codex ./my-coding-tool-optimizer --probe-only --oss --local-provider ollama --model gpt-oss:20b
```

Use this when you want to verify the environment, provider, and model path before running a benchmark.

## `inspect`

Inspect one completed run:

```bash
uv run metaharness inspect ./examples/python_fixture_benchmark/runs/hosted-codex-20260401
```

This is the quickest human-readable view of:

- candidate outcomes
- validity
- proposal application
- scope violations
- objective scores

## `ledger`

Export the per-candidate ledger for one run:

```bash
uv run metaharness ledger ./examples/python_fixture_benchmark/runs/hosted-codex-20260401
```

TSV export:

```bash
uv run metaharness ledger ./examples/python_fixture_benchmark/runs/hosted-codex-20260401 --tsv
```

Use this when you want one row per candidate with outcomes, changed-file counts, summaries, and scope violations.

## `summarize`

Summarize all runs in a project:

```bash
uv run metaharness summarize ./examples/python_fixture_benchmark
```

TSV export:

```bash
uv run metaharness summarize ./examples/python_fixture_benchmark --tsv
```

Use this when you want a project-wide view of scores, durations, and outcome counts.

## `compare`

Compare specific run directories:

```bash
uv run metaharness compare \
  ./examples/python_fixture_benchmark/runs/hosted-codex-20260401 \
  ./examples/python_fixture_benchmark/runs/ollama-20b-20260401 \
  ./examples/python_fixture_benchmark/runs/ollama-120b-20260401
```

TSV export:

```bash
uv run metaharness compare \
  ./examples/python_fixture_benchmark/runs/hosted-codex-20260401 \
  ./examples/python_fixture_benchmark/runs/ollama-120b-20260401 \
  --tsv
```

Use this when you want an explicit side-by-side comparison between selected runs rather than every run in a project.

## Output Files To Know

The most useful stored artifacts are usually:

- `run_config.json`
- `indexes/leaderboard.json`
- `manifest.json`
- `proposal/result.json`
- `proposal/workspace.diff`
- `validation/result.json`
- `evaluation/result.json`
