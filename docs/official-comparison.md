# Official Repo Comparison

This page provides a concrete comparison between:

- Official Meta-Harness reference implementation: [`stanford-iris-lab/meta-harness`](https://github.com/stanford-iris-lab/meta-harness)
- This repository: [`SuperagenticAI/metaharness`](https://github.com/SuperagenticAI/metaharness)

Use this as a decision guide for demos, internal alignment, and integration planning.

## Scope And Intent

Official repository (`stanford-iris-lab/meta-harness`):

- Canonical research reference for the paper implementation.
- Designed to replicate paper experiments and bootstrap brand-new domains.
- Emphasizes domain onboarding and research workflow structure.
- Default proposer in the shipped examples is Claude Code.
- As of 2026-07-11, includes an experimental Harbor pilot at `experimental/harbor_meta_harness` (Harbor 0.18, suites `tb2-easy`, `humanevalfix-lite`, `codepde`).

This repository (`SuperagenticAI/metaharness`):

- Production-oriented Python package and CLI for agentic coding harness optimization.
- Emphasizes repeatable runs, artifact storage, and operational tooling.
- Focuses on coding-tool style domains with deterministic checks and inspectable ledgers.
- Codex is the validated proposer. Gemini CLI and Omnigent are experimental. Pi and OpenCode were removed in 0.2.0.
- There is not yet a first-class Claude Code proposer or a Harbor / Terminal-Bench evaluator adapter.

## Feature-Level Differences

Domain onboarding:

- Official: onboarding-first flow (`ONBOARDING.md` + domain planning).
- This repo: official-style onboarding generation via `metaharness onboard`.

Optimization loop shape:

- Official: research-oriented domain loops and paper example flows.
- This repo: library-grade optimization engine with stable CLI workflows and run folders.

Evaluation stages:

- Official: explicit split between search-time and held-out test-time evaluation patterns. Terminal-Bench 2 runs go through [Harbor](https://github.com/laude-institute/harbor).
- This repo: implemented split evaluation (`search_result.json` and optional `test_result.json`) through adapter hooks. Built-in benchmarks are small deterministic coding-tool targets, not Harbor datasets.

Candidate search policy:

- Official: supports richer search patterns in research flows.
- This repo: supports `hill-climb` and `frontier` modes, batch proposals, and `single` or `pareto` selection policy.

Telemetry and experiment analysis:

- Official: paper/reference-grade analysis in example stacks.
- This repo: operational telemetry in candidate records and CLI exports (`inspect`, `ledger`, `summarize`, `compare`, `experiment`).

Provider orientation:

- Official: Claude Code wrapper in the reference examples (paper runs used Opus 4.6).
- This repo: Codex-first validated path, with Gemini CLI and Omnigent as experimental backends, plus `backend_plugins` for closed-source adapters.

Packaging and usability:

- Official: lightweight reference implementation for research adaptation.
- This repo: installable package (`superagentic-metaharness`) with operational CLI surface.

## 2026 Landscape

These projects sit next to this library. They are not features of this repository.

- Paper: [Meta-Harness: End-to-End Optimization of Model Harnesses](https://arxiv.org/abs/2603.28052) (Lee, Nair, Zhang, Lee, Khattab, Finn, 2026). ICML 2026 workshop poster: [Post-Training Reliable Agent Systems via Harness Search](https://icml.cc/virtual/2026/67972).
- Official TB2 artifact: [`stanford-iris-lab/meta-harness-tbench2-artifact`](https://github.com/stanford-iris-lab/meta-harness-tbench2-artifact) (76.4% on Terminal-Bench 2.0 with Opus 4.6, mostly environment bootstrap on Terminus-KIRA).
- [Harbor](https://github.com/laude-institute/harbor): eval runtime for Terminal-Bench 2 and related agent suites. The official Meta-Harness repo now pilots Harbor as an outer-loop substrate. This library does not wrap `harbor run` yet.
- [Harness Forge](https://github.com/001TMF/harness-forge): independent Claude Code skill reimplementation of the Meta-Harness loop.
- [AHE](https://arxiv.org/abs/2604.25850) ([code](https://github.com/china-qijizhifeng/agentic-harness-engineering)): component-level harness evolution with change manifests. This repo already stores AHE-style manifests; it does not implement AHE's seven-component tracks or rollback-on-failed-attribution.
- [HarnessCompass](https://arxiv.org/abs/2608.01918) (August 2026): generalization gate against task-ID / test-name overfitting, plus component-wise tracks. Not implemented here. A leakage audit on `inspect` is the smallest credible step.
- [Wang et al., Rethinking the Evaluation of Harness Evolution](https://arxiv.org/abs/2607.12227) ([code](https://github.com/rethinking-harness-evolution), 14 July 2026): on Terminal-Bench 2.1, AHE-style evolution often does not beat matched-budget sampling. This is why search/test splits should stay first-class, and why future `compare` baselines should include Best-of-N / sequential refine under the same budget.

This repository is listed on the official Meta-Harness README as the Codex community implementation.

## Use-Case Fit

Use the official repo first when:

- You want paper-faithful baselines and reference architecture.
- You are defining a new non-coding domain from scratch.
- You need to align terminology and flow to the canonical release.
- You need Harbor / Terminal-Bench 2 numbers against Claude Code.

Use this repo first when:

- You need a production-ready CLI workflow for coding harnesses.
- You want deterministic artifact storage for every candidate and run.
- You need Codex (hosted or local Ollama) plus repeated experiment matrices in one package.

Use both together when:

- You want official onboarding and domain framing, then operationalize with this repo.
- You want to preserve research alignment while shipping practical optimization pipelines.

## Integration Strategy

Recommended strategy is additive, not replacement:

1. Use official-style onboarding to define domain boundaries, metrics, and leakage constraints.
2. Implement domain logic through this repo's adapter hooks (`validate`, `evaluate_search`, `evaluate_test`).
3. Start in `hill-climb` mode for cost control; move to `frontier` + `pareto` when multi-objective tradeoffs matter.
4. Use `inspect` and `ledger` outputs as evidence for keep/discard decisions and regression tracking.
5. Treat Harbor, Claude Code, and a generalization-gate inspect audit as the next alignment work, not as already-shipped surfaces.

## Terminology Mapping

- Official "domain onboarding" maps to: `metaharness onboard` and `domain_spec.md`.
- Official "search/test separation" maps to: `evaluate_search` and `evaluate_test` adapter contract.
- Official "multi-objective frontier behavior" maps to: `search_mode=frontier` and `selection_policy=pareto`.
- Official "experiment analysis" maps to: `metaharness experiment`, `summarize`, and candidate ledger exports.
- Official Harbor / Terminal-Bench 2 loop does not yet map to a built-in adapter in this repo.

## References

- Official repository: [stanford-iris-lab/meta-harness](https://github.com/stanford-iris-lab/meta-harness)
- This repository: [SuperagenticAI/metaharness](https://github.com/SuperagenticAI/metaharness)
- Paper: [arXiv:2603.28052](https://arxiv.org/abs/2603.28052)
- Harbor: [laude-institute/harbor](https://github.com/laude-institute/harbor)
