# Getting Started

This page walks through the fastest path from a clean checkout to a real `metaharness` run that you can inspect.
It is written for newcomers first.

## Prerequisites

- Python 3.11 or newer
- [`uv`](https://docs.astral.sh/uv/)
- optional: `codex` or `gemini` CLI for live provider runs
- optional: Ollama with `gpt-oss:20b` or `gpt-oss:120b` for local runs

## Install

<div class="callout-card" markdown="1">
<strong>Recommended newcomer path</strong>

If you only want to use the released CLI, install from PyPI with `uv tool install`.
If you want to run the built-in examples from this repository, use a source checkout with `uv sync`.
</div>

Published package:

- PyPI distribution: `superagentic-metaharness`
- CLI command: `metaharness`
- import package: `metaharness`

Install the CLI from PyPI:

```bash
uv tool install superagentic-metaharness
```

Check the installed command:

```bash
metaharness --help
```

If you want to add the library to another Python project:

```bash
uv add superagentic-metaharness
```

<div class="callout-card" markdown="1">
<strong>Command formatting note</strong>

Long commands on this page are wrapped with `\` so they stay readable on narrower screens.
You can copy them exactly as written.
</div>

If you are working from a source checkout of this repository, create the project environment with:

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
uv run metaharness run \
  examples/python_fixture_benchmark \
  --backend fake \
  --budget 1 \
  --run-name first-run
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
uv run metaharness inspect \
  examples/python_fixture_benchmark/runs/first-run
```
</div>
<div class="command-card" markdown="1">
### Export The Candidate Ledger

Use this when you want one row per candidate with outcomes, changed-file counts, and validation or evaluation summaries.
When candidates write AHE-style change manifests, the ledger also includes manifest validity,
component labels, and attribution verdict counts.

```bash
uv run metaharness ledger \
  examples/python_fixture_benchmark/runs/first-run \
  --tsv
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
uv run metaharness experiment \
  --config examples/experiment_configs/fake-benchmarks.json
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
uv run metaharness run \
  examples/python_fixture_benchmark \
  --backend codex \
  --hosted \
  --budget 1 \
  --run-name hosted-codex
```
</div>
</div>

Use `--hosted` if a project config defaults to local Ollama.
Hosted Codex is the strongest current path for real benchmark runs in this repository.

## Use Trace Evidence

If you have a HALO-style trace diagnosis report, pass it to the run with
`--trace-evidence`. A common workflow is to generate `trace_evidence.md` with
`rlm-code`'s `trace_analysis` environment, then use that report to guide
`metaharness` candidate proposals.

```bash
uv run metaharness run \
  examples/python_fixture_benchmark \
  --backend codex \
  --hosted \
  --trace-evidence ./trace_evidence.md \
  --budget 1 \
  --run-name trace-grounded-codex
```

The report is copied into each candidate workspace at
`.metaharness/evidence/trace_evidence.md` and embedded in the proposer prompt.
Use this when trace analysis has surfaced concrete harness failures such as
hallucinated tool calls, redundant arguments, refusal loops, or semantic
correctness issues.

Each proposer is also instructed to write `.metaharness/change_manifest.json`
before finishing. MetaHarness archives that file under
`candidates/<id>/proposal/change_manifest.json`. If your evaluator returns
`EvaluationResult(metadata={"task_results": {...}})`, MetaHarness writes
`proposal/change_attribution.json` by comparing predicted fixes and risk tasks
against the candidate's actual task-level deltas.

## Use Gemini CLI

Gemini is an experimental backend in the current release.
Use it if Gemini CLI is already part of your local workflow and you are comfortable with a try-it-yourself path.

Requirements:

- `gemini` CLI installed
- Gemini authentication configured in your local environment

<div class="command-grid" markdown="1">
<div class="command-card" markdown="1">
### Probe The CLI

```bash
uv run metaharness smoke gemini examples/python_fixture_benchmark --probe-only
```
</div>
<div class="command-card" markdown="1">
### Run Gemini

```bash
uv run metaharness run \
  examples/python_fixture_benchmark \
  --backend gemini \
  --model gemini-2.5-pro \
  --proposal-timeout 180 \
  --budget 1 \
  --run-name gemini-run
```
</div>
</div>

The integration is real, but it is not part of the main validated Codex-first release path.

## Use Local Codex Over Ollama

Requirements:

- Ollama server reachable on `127.0.0.1:11434`
- a local model such as `gpt-oss:20b` or `gpt-oss:120b`

<div class="command-grid" markdown="1">
<div class="command-card" markdown="1">
### Probe The Local Path

```bash
uv run metaharness smoke codex \
  examples/python_fixture_benchmark \
  --probe-only \
  --oss \
  --local-provider ollama \
  --model gpt-oss:20b
```
</div>
<div class="command-card" markdown="1">
### Run `gpt-oss:20b`

```bash
uv run metaharness run \
  examples/python_fixture_benchmark \
  --backend codex \
  --oss \
  --local-provider ollama \
  --model gpt-oss:20b \
  --proposal-timeout 240 \
  --budget 1 \
  --run-name ollama-20b
```
</div>
<div class="command-card" markdown="1">
### Run `gpt-oss:120b`

```bash
uv run metaharness run \
  examples/python_fixture_benchmark \
  --backend codex \
  --oss \
  --local-provider ollama \
  --model gpt-oss:120b \
  --proposal-timeout 420 \
  --budget 1 \
  --run-name ollama-120b
```
</div>
</div>

## Create Your Own Project

If you want to optimize your own coding-agent harness, scaffold a project:

```bash
uv run metaharness scaffold coding-tool ./my-coding-tool-optimizer
```

If you want to use a closed-source or internal harness, add a plugin backend in `metaharness.json` under `backend_plugins` and run it with `--backend <name>`.
See [Extensions](extensions.md) for the factory contract.

Available scaffold profiles:

- `standard`
- `local-oss-smoke`
- `local-oss-medium`

Examples:

```bash
uv run metaharness scaffold \
  coding-tool \
  ./my-local-oss-smoke \
  --profile local-oss-smoke

uv run metaharness scaffold \
  coding-tool \
  ./my-local-oss-medium \
  --profile local-oss-medium
```

If you are defining a brand-new domain and want an official-style planning workflow first, create a domain onboarding pack:

```bash
uv run metaharness onboard ./my-domain-onboarding
```

This writes `ONBOARDING.md` and `domain_spec.md` so search/test splits, metrics, and leakage risks are defined before implementation.

If you want a checked-in experiment workflow for your own project, add a small JSON spec and run:

```bash
uv run metaharness experiment \
  --config ./my-experiment.json
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
