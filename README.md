# metaharness

[![CI](https://github.com/SuperagenticAI/metaharness/actions/workflows/ci.yml/badge.svg)](https://github.com/SuperagenticAI/metaharness/actions/workflows/ci.yml)
[![Docs](https://github.com/SuperagenticAI/metaharness/actions/workflows/pages.yml/badge.svg)](https://github.com/SuperagenticAI/metaharness/actions/workflows/pages.yml)
[![Documentation](https://img.shields.io/badge/docs-GitHub%20Pages-111111?logo=github&logoColor=white)](https://superagenticai.github.io/metaharness/)
[![PyPI](https://img.shields.io/pypi/v/superagentic-metaharness)](https://pypi.org/project/superagentic-metaharness/)
[![Python](https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white)](https://github.com/SuperagenticAI/metaharness/blob/main/pyproject.toml)
[![License](https://img.shields.io/github/license/SuperagenticAI/metaharness)](https://github.com/SuperagenticAI/metaharness/blob/main/LICENSE)
[![Status](https://img.shields.io/badge/status-alpha-F59E0B)](https://github.com/SuperagenticAI/metaharness)
[![Paper](https://img.shields.io/badge/paper-Meta%20Harness-B31B1B)](https://arxiv.org/pdf/2603.28052)

`metaharness` is an open source Python library for optimizing executable harnesses around agentic coding systems.
It is inspired by the [Meta Harness paper](https://arxiv.org/pdf/2603.28052) and is an unofficial open source implementation of the core ideas in that work.
The current benchmark evidence in this repository is centered on the Codex CLI path, including hosted Codex and Codex over local Ollama models.
Codex is the primary and validated backend in this repository today.
Gemini CLI is the only additional experimental integration.

It is built for teams who want to improve the code and files around an agent workflow, not just the prompt.
That includes instruction files, setup flows, validation scripts, test scripts, routing logic, and other executable support code.

## Why `metaharness`

Many agent failures come from the harness around the model:

- weak repository instructions
- missing setup steps
- broken validation logic
- incomplete test flows
- poor iteration memory
- acceptance checks that do not match the real task

`metaharness` turns those artifacts into a repeatable optimization target with stored evidence for every proposal.
It also captures a compact environment snapshot before each proposal so agents do not waste early turns on basic workspace discovery.
Projects can also declare an allowed write scope so off-target edits are rejected automatically.

## How It Works

`metaharness` runs an outer optimization loop around a harness:

1. start from a baseline workspace
2. ask a coding agent to improve it
3. validate and evaluate the result
4. keep the best candidate
5. store all artifacts on disk

The result is a practical, inspectable workflow for improving real harnesses instead of ad hoc prompt tinkering.

## Who It Is For

- developers building agentic coding systems who want to optimize harness code, workflow scripts, retrieval wrappers, routing, and evaluation flows
- practitioners using coding-agent tools who want to improve `AGENTS.md`, `GEMINI.md`, bootstrap scripts, validation scripts, and acceptance tests

## Quickstart

Install the published CLI from PyPI:

```bash
uv tool install superagentic-metaharness
```

Check the command:

```bash
metaharness --help
```

If you want to run the built-in examples in this repository, use a source checkout:

```bash
uv sync
```

Run the fake backend on a real benchmark:

```bash
uv run metaharness run \
  examples/python_fixture_benchmark \
  --backend fake \
  --budget 1 \
  --run-name quickstart
```

Inspect the run:

```bash
uv run metaharness inspect \
  examples/python_fixture_benchmark/runs/quickstart
```

Export the candidate ledger:

```bash
uv run metaharness ledger \
  examples/python_fixture_benchmark/runs/quickstart \
  --tsv
```

Run a saved experiment matrix:

```bash
uv run metaharness experiment \
  --config examples/experiment_configs/fake-benchmarks.json
```

## Core Capabilities

- a minimal optimization engine
- a filesystem-backed run store
- automatic environment bootstrap snapshots for each proposal
- optional write-scope enforcement through `allowed_write_paths`
- a provider-neutral proposer backend interface
- a real `CodexExecBackend`
- an experimental `GeminiCliBackend`
- a deterministic `FakeBackend`
- extension backends via `backend_plugins` (`module:callable` factories)
- a coding-tool integration for instruction files and script-based harnesses
- explicit per-candidate outcomes: `keep`, `discard`, `crash`, `timeout`, `no-change`, and `scope-violation`
- reporting commands for `inspect`, `ledger`, `summarize`, and `compare`
- experiment-matrix execution with JSON and TSV outputs
- benchmark targets and experiment records

## Current Status

The repository currently includes:

- two real coding-tool benchmark targets
- a smaller deterministic ticket-router example
- hosted Codex runs on the real benchmarks
- local Codex over Ollama runs with `gpt-oss:20b` and `gpt-oss:120b`
- a docs site published from GitHub Actions

Current documented experiments in this repository show:

- hosted Codex solves both real benchmarks in one proposal iteration
- local `gpt-oss:120b` solves `python_fixture_benchmark`
- local `gpt-oss:20b` is useful for smoke checks but timed out on the current real benchmark runs

Detailed experiment records:

- [Benchmark overview](BENCHMARKS.md)
- [Recorded benchmark results](BENCHMARK_RESULTS.md)
- [Experiment notes](docs/experiments.md)

## Provider Status

- Codex is the main validated harness path in this repository today
- hosted Codex is the strongest current path for real runs
- local Codex over Ollama works and has been exercised with `gpt-oss:20b` and `gpt-oss:120b`
- Gemini is implemented as an experimental backend and is not part of the main validated release path

All real provider results currently documented in this repository were produced through the Codex CLI path.
That includes both hosted Codex runs and local Ollama runs driven through Codex with `gpt-oss` models.
Other coding-agent evaluations in the wider ecosystem often emphasize Claude Code and Opus, but this repository's current benchmark evidence is Codex-first.

## Documentation

- [Project documentation](https://superagenticai.github.io/metaharness/)
- [Getting started](https://superagenticai.github.io/metaharness/getting-started/)
- [Architecture](https://superagenticai.github.io/metaharness/architecture/)
- [Providers](https://superagenticai.github.io/metaharness/providers/)
- [Extensions](https://superagenticai.github.io/metaharness/extensions/)
- [Benchmarks](https://superagenticai.github.io/metaharness/benchmarks/)
- [Official comparison](https://superagenticai.github.io/metaharness/official-comparison/)
- [Alignment](https://superagenticai.github.io/metaharness/alignment/)
- [CLI reference](https://superagenticai.github.io/metaharness/cli-reference/)
- [Experiments](https://superagenticai.github.io/metaharness/experiments/)

## Installation

Published package:

- PyPI distribution: `superagentic-metaharness`
- CLI command: `metaharness`
- import package: `metaharness`

Install the CLI with `uv`:

```bash
uv tool install superagentic-metaharness
```

Upgrade it later:

```bash
uv tool upgrade superagentic-metaharness
```

Install it into a Python project dependency set:

```bash
uv add superagentic-metaharness
```

Install with `pip`:

```bash
pip install superagentic-metaharness
```

Source checkout setup:

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

Editable install with `pip` also works:

```bash
pip install -e .
```

## Hosted Codex

Requirements:

- `codex` CLI installed
- authenticated Codex session or API key
- outbound network access

Run a real benchmark with hosted Codex:

```bash
uv run metaharness run \
  examples/python_fixture_benchmark \
  --backend codex \
  --hosted \
  --budget 1 \
  --run-name hosted-codex
```

Important:

- use `--hosted` when a project config defaults to local Ollama
- the library is ready for hosted Codex runs today

## Local Codex Over Ollama

Probe the local setup:

```bash
uv run metaharness smoke codex \
  examples/python_fixture_benchmark \
  --probe-only \
  --oss \
  --local-provider ollama \
  --model gpt-oss:20b
```

Run with `gpt-oss:20b`:

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

Run with `gpt-oss:120b`:

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

## Benchmarks And Examples

Real benchmarks:

- [examples/python_fixture_benchmark](examples/python_fixture_benchmark)
- [examples/python_cli_benchmark](examples/python_cli_benchmark)

Smaller deterministic example:

- [examples/ticket_router](examples/ticket_router)

Run the ticket router example:

```bash
uv run python examples/ticket_router/run.py --backend fake --budget 1
```

## Scaffold Your Own Project

Create a coding-tool project:

```bash
uv run metaharness scaffold coding-tool ./my-coding-tool-optimizer
```

Available profiles:

- `standard`
- `local-oss-smoke`
- `local-oss-medium`

Run the scaffold with the fake backend:

```bash
uv run metaharness run ./my-coding-tool-optimizer --backend fake --budget 1
```

## Backend Extensions

You can register custom closed-source or internal harness adapters without editing `metaharness` core code.

Add a plugin in `metaharness.json`:

```json
{
  "backend_plugins": {
    "cursor": {
      "factory": "my_harness_plugins.cursor:create_backend",
      "options": {
        "model": "cursor-pro"
      }
    }
  }
}
```

Then run it like any other backend:

```bash
uv run metaharness run ./my-coding-tool-optimizer --backend cursor --budget 1
```

Factory contract:

- reference format: `module:callable`
- callable receives `project` and `options`
- callable returns an object with `name`, `prepare`, `invoke`, and `collect`

Create an official-style domain onboarding pack:

```bash
uv run metaharness onboard ./my-domain-onboarding
```

This writes:

- `ONBOARDING.md` with a question-driven domain setup flow
- `domain_spec.md` with a structured template for search and evaluation design

## CLI Overview

Create a scaffold:

```bash
uv run metaharness scaffold coding-tool ./my-project
```

Run a project:

```bash
uv run metaharness run ./my-project --backend fake --budget 1
```

Probe Codex:

```bash
uv run metaharness smoke codex ./my-project --probe-only
```

Inspect a run:

```bash
uv run metaharness inspect ./my-project/runs/example
```

Compare runs:

```bash
uv run metaharness compare \
  ./examples/python_fixture_benchmark/runs/hosted-codex-20260401 \
  ./examples/python_fixture_benchmark/runs/ollama-20b-20260401 \
  ./examples/python_fixture_benchmark/runs/ollama-120b-20260401
```

Run an experiment matrix:

```bash
uv run metaharness experiment --config examples/experiment_configs/fake-benchmarks.json
```

## Benefits Of The Filesystem Approach

Every run stores:

- prompts
- candidate workspaces
- validation results
- evaluation results
- proposal metadata
- workspace diffs
- per-candidate manifests

That makes the optimization history reviewable, debuggable, and reusable.

## Development

Compile checks:

```bash
uv run python -m compileall -q src tests examples docs
```

Unit tests:

```bash
uv run python -m unittest discover -s tests -v
```

Docs build:

```bash
uv run mkdocs build --strict
```

Fake benchmark smoke runs:

```bash
uv run metaharness run examples/python_fixture_benchmark --backend fake --budget 1 --run-name ci-fixture-local
uv run metaharness run examples/python_cli_benchmark --backend fake --budget 1 --run-name ci-cli-local
uv run python examples/ticket_router/run.py --backend fake --budget 1
```

## License

Apache 2.0. See [LICENSE](LICENSE).
