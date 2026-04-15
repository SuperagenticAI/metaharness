# Official Repo Comparison

This page provides a concrete comparison between:

- Official Meta-Harness reference implementation: `stanford-iris-lab/meta-harness`
- This repository: `SuperagenticAI/metaharness`

Use this as a decision guide for demos, internal alignment, and integration planning.

## Scope And Intent

Official repository (`stanford-iris-lab/meta-harness`):

- Canonical research reference for the paper implementation.
- Designed to replicate paper experiments and bootstrap brand-new domains.
- Emphasizes domain onboarding and research workflow structure.

This repository (`SuperagenticAI/metaharness`):

- Production-oriented Python package and CLI for agentic coding harness optimization.
- Emphasizes repeatable runs, artifact storage, and operational tooling.
- Focuses on coding-tool style domains with deterministic checks and inspectable ledgers.

## Feature-Level Differences

Domain onboarding:

- Official: onboarding-first flow (`ONBOARDING.md` + domain planning).
- This repo: now supports official-style onboarding generation via `metaharness onboard`.

Optimization loop shape:

- Official: research-oriented domain loops and paper example flows.
- This repo: library-grade optimization engine with stable CLI workflows and run folders.

Evaluation stages:

- Official: explicit split between search-time and held-out test-time evaluation patterns.
- This repo: implemented split evaluation (`search_result.json` and optional `test_result.json`) through adapter hooks.

Candidate search policy:

- Official: supports richer search patterns in research flows.
- This repo: supports `hill-climb` and `frontier` modes, batch proposals, and `single` or `pareto` selection policy.

Telemetry and experiment analysis:

- Official: paper/reference-grade analysis in example stacks.
- This repo: operational telemetry in candidate records and CLI exports (`inspect`, `ledger`, `summarize`, `compare`, `experiment`).

Provider orientation:

- Official: default proposer flow centered around its reference setup.
- This repo: Codex-first validated path, with Gemini/Pi/OpenCode available as experimental integrations.

Packaging and usability:

- Official: lightweight reference implementation for research adaptation.
- This repo: installable package (`superagentic-metaharness`) with operational CLI surface.

## Use-Case Fit

Use the official repo first when:

- You want paper-faithful baselines and reference architecture.
- You are defining a new non-coding domain from scratch.
- You need to align terminology and flow to the canonical release.

Use this repo first when:

- You need a production-ready CLI workflow for coding harnesses.
- You want deterministic artifact storage for every candidate and run.
- You need provider integration and repeated experiment matrices in one package.

Use both together when:

- You want official onboarding and domain framing, then operationalize with this repo.
- You want to preserve research alignment while shipping practical optimization pipelines.

## Integration Strategy

Recommended strategy is additive, not replacement:

1. Use official-style onboarding to define domain boundaries, metrics, and leakage constraints.
2. Implement domain logic through this repo's adapter hooks (`validate`, `evaluate_search`, `evaluate_test`).
3. Start in `hill-climb` mode for cost control; move to `frontier` + `pareto` when multi-objective tradeoffs matter.
4. Use `inspect` and `ledger` outputs as evidence for keep/discard decisions and regression tracking.

## Terminology Mapping

- Official "domain onboarding" maps to: `metaharness onboard` and `domain_spec.md`.
- Official "search/test separation" maps to: `evaluate_search` and `evaluate_test` adapter contract.
- Official "multi-objective frontier behavior" maps to: `search_mode=frontier` and `selection_policy=pareto`.
- Official "experiment analysis" maps to: `metaharness experiment`, `summarize`, and candidate ledger exports.

## References

- Official repository: <https://github.com/stanford-iris-lab/meta-harness>
- This repository: <https://github.com/SuperagenticAI/metaharness>
- Paper: <https://arxiv.org/pdf/2603.28052>
