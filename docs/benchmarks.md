# Benchmarks

## Overview

`metaharness` currently includes several example targets.

Two are real coding-tool benchmarks:

- `python_fixture_benchmark`
- `python_cli_benchmark`

Omnigent-shaped examples:

- `omnigent_agent_benchmark` (declarative agent config)
- `omnigent_routing_benchmark` (JSON harness+model routing table)

One is a smaller deterministic example:

- `ticket_router`

Host embed (library call, not a benchmark loop of its own):

- `embed_runtime`

## `python_fixture_benchmark`

Path:

- `examples/python_fixture_benchmark`

What it exercises:

- a real `python -m venv` bootstrap flow
- a real `unittest` suite over a fixture package
- deterministic instruction-file checks
- helper script correctness

What can change:

- `AGENTS.md`
- `GEMINI.md`
- `scripts/bootstrap.sh`
- `scripts/validate.sh`
- `scripts/test.sh`

Configured write scope:

- `AGENTS.md`
- `GEMINI.md`
- `scripts/`

Typical runs:

```bash
uv run metaharness run examples/python_fixture_benchmark --backend fake --budget 1
uv run metaharness run \
  examples/python_fixture_benchmark \
  --backend codex \
  --hosted \
  --budget 1
uv run metaharness run \
  examples/python_fixture_benchmark \
  --backend codex \
  --oss \
  --local-provider ollama \
  --model gpt-oss:120b \
  --proposal-timeout 420 \
  --budget 1
```

## `python_cli_benchmark`

Path:

- `examples/python_cli_benchmark`

What it exercises:

- a real `python -m venv` bootstrap flow
- a real `unittest` suite
- a real CLI smoke command against fixture data
- deterministic instruction-file checks

What can change:

- `AGENTS.md`
- `GEMINI.md`
- `scripts/bootstrap.sh`
- `scripts/validate.sh`
- `scripts/test.sh`

Configured write scope:

- `AGENTS.md`
- `GEMINI.md`
- `scripts/`

Typical runs:

```bash
uv run metaharness run examples/python_cli_benchmark --backend fake --budget 1
uv run metaharness run \
  examples/python_cli_benchmark \
  --backend codex \
  --hosted \
  --budget 1
uv run metaharness run \
  examples/python_cli_benchmark \
  --backend codex \
  --oss \
  --local-provider ollama \
  --model gpt-oss:20b \
  --proposal-timeout 240 \
  --budget 1
```

## `omnigent_routing_benchmark`

Path:

- `examples/omnigent_routing_benchmark`

What it exercises:

- an Omnigent-shaped `routes:select` JSON table as the candidate surface
- command tasks that call a stable `route.py` CLI
- leakage gate against copying task IDs into `routing.json`
- single-class middleware write scope (`routing.json` only)

This is not a live Omnigent server. The table is the optimization target.

Typical run:

```bash
uv run metaharness run examples/omnigent_routing_benchmark --backend fake --budget 1
```

## `ticket_router`

Path:

- `examples/ticket_router`

This is a smaller deterministic example that optimizes a Python router against a fixed dataset.
It is useful for fast development checks and basic API examples.

Run it:

```bash
uv run python examples/ticket_router/run.py --backend fake --budget 1
```

## Scaffold Profiles

The CLI scaffold also includes profiles for users who want to bring their own coding-tool project:

- `standard`
- `local-oss-smoke`
- `local-oss-medium`

These are useful for starting a real project, but the benchmark directories are the clearest examples of how to structure a reusable target.
