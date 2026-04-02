<div class="hero">
  <p class="hero-kicker">Filesystem first harness optimization</p>
  <h1>metaharness</h1>
  <p>
    <code>metaharness</code> is an open source Python library for optimizing executable harnesses around agentic coding systems.
    It treats the harness itself as the optimization target, not just the prompt.
    That includes instruction files, bootstrap scripts, validation scripts, test flows, routing logic, and other executable support code.
  </p>
  <div class="hero-actions">
    <a class="md-button md-button--primary" href="getting-started/">Get Started</a>
    <a class="md-button" href="cli-reference/">Explore The CLI</a>
    <a class="md-button" href="experiments/">See Experiment Results</a>
  </div>
</div>

<div class="stat-grid">
  <div class="stat-card">
    <strong>2 real benchmarks</strong>
    Real coding-tool targets built around fixture repos, shell scripts, and deterministic acceptance checks.
  </div>
  <div class="stat-card">
    <strong>Codex-first today</strong>
    Hosted Codex and local Codex over Ollama have both been exercised in real runs.
  </div>
  <div class="stat-card">
    <strong>Filesystem evidence</strong>
    Every run stores prompts, manifests, diffs, evaluation output, and candidate history on disk.
  </div>
  <div class="stat-card">
    <strong>Experiment runner included</strong>
    Batch runs, candidate ledgers, JSON output, and TSV exports are already part of the CLI.
  </div>
</div>

## Why This Exists

<p class="section-intro">
Most agent workflows do not fail because the base model is incapable.
They fail because the surrounding harness is weak, incomplete, or inconsistent.
The problem is often outside the core model call.
</p>

<div class="feature-grid" markdown="1">
<div class="feature-card" markdown="1">
**Weak repository instructions**

Agents start with incomplete context, make risky assumptions, or waste time rediscovering basics.
</div>
<div class="feature-card" markdown="1">
**Broken setup and validation**

Bootstrap scripts, validation steps, and test flows drift away from the workflow they are supposed to guard.
</div>
<div class="feature-card" markdown="1">
**No durable experiment record**

Teams try improvements, but they cannot easily compare what changed, what improved, and what failed.
</div>
<div class="feature-card" markdown="1">
**No write-scope discipline**

An optimizer may edit the wrong files and still produce noisy or misleading results.
</div>
</div>

`metaharness` addresses these problems by making the harness executable, inspectable, and benchmarkable.
It captures a compact environment bootstrap before each proposal, stores every candidate on disk, and can enforce an explicit write scope through `allowed_write_paths`.

## What It Optimizes

<div class="callout-card" markdown="1">
<strong>The optimized object is the harness, not only the prompt.</strong>

Typical targets include `AGENTS.md`, `GEMINI.md`, bootstrap scripts, validation scripts, test scripts, routing code, benchmark glue, and other files that shape how an agent actually works in a repository.
</div>

## How The Loop Works

<div class="flow-grid" markdown="1">
<div class="flow-card" markdown="1">
<span class="flow-step">1</span>
**Materialize a baseline**

Start from a baseline workspace that already represents a real harness.
</div>
<div class="flow-card" markdown="1">
<span class="flow-step">2</span>
**Capture context**

Collect a compact environment snapshot and parent-candidate feedback before the proposer edits anything.
</div>
<div class="flow-card" markdown="1">
<span class="flow-step">3</span>
**Propose, validate, evaluate**

Ask a coding agent to improve the workspace, then validate and score the result with deterministic checks.
</div>
<div class="flow-card" markdown="1">
<span class="flow-step">4</span>
**Keep evidence**

Store diffs, manifests, ledgers, outcomes, and summaries on disk so the run can be audited and compared later.
</div>
</div>

## Core Capabilities

<div class="feature-grid" markdown="1">
<div class="feature-card" markdown="1">
**Optimization engine**

A small outer loop that keeps the best candidate according to a deterministic objective.
</div>
<div class="feature-card" markdown="1">
**Filesystem-backed run store**

Run configs, candidate workspaces, manifests, diffs, and stage results are stored in a stable on-disk layout.
</div>
<div class="feature-card" markdown="1">
**Environment bootstrap snapshots**

Each proposal gets a compact view of the workspace, tools, package files, git state, and system facts before it starts editing.
</div>
<div class="feature-card" markdown="1">
**Write-scope enforcement**

Projects can declare the files or directories that are allowed to change and reject scope violations automatically.
</div>
<div class="feature-card" markdown="1">
**Explicit candidate outcomes**

Runs classify candidates as `keep`, `discard`, `crash`, `timeout`, `no-change`, or `scope-violation`.
</div>
<div class="feature-card" markdown="1">
**Experiment runner**

Run repeated trial matrices across benchmarks, providers, budgets, and models with JSON and TSV outputs.
</div>
</div>

## Supported Release Shape

<p class="section-intro">
The current package is strongest in a Codex-first setup.
Hosted Codex is the most reliable current path for real benchmark runs in this repository.
Local Codex over Ollama has also been exercised with `gpt-oss:20b` and `gpt-oss:120b`.
</p>

Gemini exists as a backend scaffold, but it is not yet at parity with the Codex path.

## Built-In Targets

- `examples/python_fixture_benchmark`
- `examples/python_cli_benchmark`
- `examples/ticket_router`

The two Python benchmarks are the main release-quality examples.
They use real shell scripts, real fixture repositories, and deterministic acceptance checks rather than placeholder text-only scoring.

## Start Here

<div class="command-grid" markdown="1">
<div class="command-card" markdown="1">
### First Useful Run

Run the fake backend on a real benchmark to see the full loop without provider dependencies.

```bash
uv run metaharness run examples/python_fixture_benchmark --backend fake --budget 1 --run-name first-run
```
</div>
<div class="command-card" markdown="1">
### Inspect What Happened

Look at the winning candidate, run summary, and candidate ledger.

```bash
uv run metaharness inspect examples/python_fixture_benchmark/runs/first-run
uv run metaharness ledger examples/python_fixture_benchmark/runs/first-run --tsv
```
</div>
<div class="command-card" markdown="1">
### Run An Experiment Matrix

Use a saved config to run repeated trials and write JSON plus TSV outputs.

```bash
uv run metaharness experiment --config examples/experiment_configs/fake-benchmarks.json
```
</div>
</div>

## Continue Reading

- [Getting Started](getting-started.md)
- [Architecture](architecture.md)
- [Providers](providers.md)
- [Benchmarks](benchmarks.md)
- [CLI Reference](cli-reference.md)
- [Experiments](experiments.md)
