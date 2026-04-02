# Getting Started

This page walks through the fastest path from a clean checkout to a real `metaharness` run that you can inspect.

## Prerequisites

- Python 3.11 or newer
- [`uv`](https://docs.astral.sh/uv/)
- optional: `codex` CLI for hosted or local Codex runs
- optional: Ollama with `gpt-oss:20b` or `gpt-oss:120b` for local runs

## Install

Use `uv` to create the project environment:

```bash
uv sync
```

If you want the docs toolchain too:

```bash
uv sync --group dev
```

Check the CLI:

```bash
uv run metaharness --help
```

## The Fastest First Run

<div class="callout-card" markdown="1">
<strong>Recommended first run</strong>

Use the fake backend on a real benchmark. This exercises the full loop without needing provider auth, network access, or a local model server.
</div>

```bash
uv run metaharness run examples/python_fixture_benchmark --backend fake --budget 1 --run-name first-run
```

Expected result:

- a run directory under `examples/python_fixture_benchmark/runs/first-run`
- `best_candidate_id=c0001`
- `best_objective=1.000`

## What To Inspect Next

<div class="command-grid" markdown="1">
<div class="command-card" markdown="1">
### Inspect A Single Run

Use this when you want a quick human-readable summary of the candidates and outcomes.

```bash
uv run metaharness inspect examples/python_fixture_benchmark/runs/first-run
```
</div>
<div class="command-card" markdown="1">
### Export The Candidate Ledger

Use this when you want one row per candidate with outcomes, changed-file counts, and validation or evaluation summaries.

```bash
uv run metaharness ledger examples/python_fixture_benchmark/runs/first-run --tsv
```
</div>
<div class="command-card" markdown="1">
### Summarize A Whole Benchmark

Use this when you want one row per run and a compact view of score, duration, and failure patterns.

```bash
uv run metaharness summarize examples/python_fixture_benchmark
```
</div>
</div>

## Run A Saved Experiment Matrix

Once the single-run flow makes sense, move to repeated trials:

```bash
uv run metaharness experiment --config examples/experiment_configs/fake-benchmarks.json
```

This writes:

- `experiment.json`
- `trials.json`
- `aggregates.json`
- `trials.tsv`
- `aggregates.tsv`

Use this path when you want reproducible benchmarking rather than ad hoc manual runs.

## Use Hosted Codex

Requirements:

- `codex` CLI installed
- authenticated Codex session or API key setup
- outbound network access

<div class="command-grid" markdown="1">
<div class="command-card" markdown="1">
### Probe The CLI

```bash
uv run metaharness smoke codex examples/python_fixture_benchmark --probe-only
```
</div>
<div class="command-card" markdown="1">
### Run Hosted Codex

```bash
uv run metaharness run examples/python_fixture_benchmark --backend codex --hosted --budget 1 --run-name hosted-codex
```
</div>
</div>

Use `--hosted` if a project config defaults to local Ollama.
Hosted Codex is the strongest current path for real benchmark runs in this repository.

## Use Local Codex Over Ollama

Requirements:

- Ollama server reachable on `127.0.0.1:11434`
- a local model such as `gpt-oss:20b` or `gpt-oss:120b`

<div class="command-grid" markdown="1">
<div class="command-card" markdown="1">
### Probe The Local Path

```bash
uv run metaharness smoke codex examples/python_fixture_benchmark --probe-only --oss --local-provider ollama --model gpt-oss:20b
```
</div>
<div class="command-card" markdown="1">
### Run `gpt-oss:20b`

```bash
uv run metaharness run examples/python_fixture_benchmark --backend codex --oss --local-provider ollama --model gpt-oss:20b --proposal-timeout 240 --budget 1 --run-name ollama-20b
```
</div>
<div class="command-card" markdown="1">
### Run `gpt-oss:120b`

```bash
uv run metaharness run examples/python_fixture_benchmark --backend codex --oss --local-provider ollama --model gpt-oss:120b --proposal-timeout 420 --budget 1 --run-name ollama-120b
```
</div>
</div>

## Create Your Own Project

If you want to optimize your own coding-agent harness, scaffold a project:

```bash
uv run metaharness scaffold coding-tool ./my-coding-tool-optimizer
```

Available scaffold profiles:

- `standard`
- `local-oss-smoke`
- `local-oss-medium`

Examples:

```bash
uv run metaharness scaffold coding-tool ./my-local-oss-smoke --profile local-oss-smoke
uv run metaharness scaffold coding-tool ./my-local-oss-medium --profile local-oss-medium
```

If you want a checked-in experiment workflow for your own project, add a small JSON spec and run:

```bash
uv run metaharness experiment --config ./my-experiment.json
```

## What A Successful First Session Looks Like

By the end of a first session, you should be able to:

- run a benchmark with the fake backend
- inspect the winning candidate
- export a candidate ledger
- run a saved experiment matrix
- decide whether to use hosted Codex or a local Ollama model for the next step

## Build The Docs

Serve locally:

```bash
uv run mkdocs serve
```

Build the site:

```bash
uv run mkdocs build --strict
```
