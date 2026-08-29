# Alignment With Official Meta-Harness

This page documents how `metaharness` aligns with the official Stanford IRIS Meta-Harness release while preserving the current strengths of this repository.

## Current Position

The official repository is the canonical research reference with:

- broad domain onboarding via `ONBOARDING.md`
- paper reference experiments (text classification, Terminal-Bench 2)
- domain-specific outer loops
- Claude Code as the shipped proposer
- an experimental Harbor pilot (`experimental/harbor_meta_harness`, 2026-07-11)

This repository is a production-oriented library with:

- packaged CLI and installable Python module
- Codex-first proposer integration
- filesystem-first run store and reporting
- deterministic coding-tool benchmark workflows

The right strategy is to merge strengths, not replace one with the other.

## What Already Matches

- Harness-first optimization around a fixed model surface.
- Artifact-driven outer loop with inspectable candidate history.
- Proposer abstraction that can support multiple providers.
- Deterministic scoring as the decision signal for keep/discard behavior.
- Environment bootstrap snapshots before each proposal (the main mechanism behind the paper's Terminal-Bench 2 result).
- AHE-style change manifests on candidates.

## Main Gaps To Close

- No first-class Claude Code proposer, which is what the paper and official examples actually run.
- No Harbor / Terminal-Bench evaluator adapter, so this repo cannot reproduce the paper headline number or later AHE / HarnessCompass results.
- Leakage and generalization-gate checks are not part of `inspect` yet (task IDs, test names, keyword dispatch).
- Test-time-scaling baselines (Best-of-N / sequential refine under a matched budget) are not a `compare` mode yet. See [Wang et al. 2026](https://arxiv.org/abs/2607.12227).
- Component-wise tracks (tools and middleware vs prompt, skills, and memory) are not first-class. The workspace is still one blob.
- Provider telemetry can still be richer for research-grade analysis.

## Alignment Principles

- Keep the current CLI and package stable.
- Adopt official ideas as additive capabilities behind clear interfaces.
- Preserve coding-tool workflows as a first-class domain adapter.
- Avoid direct code vendoring from paper examples into core modules.

## What's Implemented

### Domain Onboarding
- `metaharness onboard <target_dir>` creates `ONBOARDING.md` and `domain_spec.md`
- Provides structured entry point for new domain work

### Domain Adapter API
- Generalized coding-tool integration into a domain adapter contract
- Coding-tool adapter is the default built-in implementation
- Adapter hooks for validation, search evaluation, and optional test evaluation

### Split Evaluation
- Explicit search-stage versus held-out test-stage evaluation
- Test-stage artifacts never leak to proposer context during search
- Run metadata fields record split definitions and leakage safeguards
- `search_result.json` and optional `test_result.json` in run artifacts

### Frontier and Multi-Candidate Search
- Optional batch candidate proposals per iteration
- Frontier policies beyond single scalar best, including Pareto-style policies
- Simple hill-climb mode available as the default for low-cost workflows
- Configurable via `search_mode`, `proposal_batch_size`, and `selection_policy`

### Telemetry and Experiment Upgrades
- Extended proposal telemetry with token, cost, and tool-level summaries
- Richer experiment summary outputs for multi-objective comparisons
- Token/tool/cost fields and expanded trial/summary columns in outputs

## Near-Term Roadmap

Shipped items above stay shipped. The remaining alignment work is:

1. Claude Code proposer backend, paper-faithful, next to Codex.
2. Harbor evaluator adapter so `evaluate_search` / `evaluate_test` can call `harbor run` on Terminal-Bench 2 (and later SWE-bench).
3. Leakage / generalization-gate audit in `inspect` and `summarize` (reject or flag diffs that mention task IDs, test function names, or private keyword dispatch). Inspired by [HarnessCompass](https://arxiv.org/abs/2608.01918).
4. Matched-budget sampling baseline in `compare`, so harness-evolution gains are not confused with extra search. Inspired by [Wang et al.](https://arxiv.org/abs/2607.12227).
5. Optional component tracks via `allowed_write_paths` / `domain_spec.md`, so a candidate can be constrained to tools-and-middleware or to prompt-and-skills.

## Risks And Mitigations

- Risk: overfitting core API to one research example.
- Mitigation: keep interfaces domain-agnostic and adapter-based.

- Risk: breaking current coding-tool user workflows.
- Mitigation: preserve existing commands and semantics as defaults.

- Risk: complexity jump in CLI and run layout.
- Mitigation: gate advanced modes behind explicit flags and document layouts clearly.

- Risk: reporting harness-evolution gains that are actually extra test-time search.
- Mitigation: keep search/test isolation, and add matched-budget sampling baselines before claiming Harbor/TB2 numbers.

- Risk: evolved harnesses memorizing task IDs or test names.
- Mitigation: add a generalization-gate / regex leakage audit to `inspect`.

## Success Criteria

- A new domain can be scoped using onboarding files before any code changes.
- At least one adapter can run with explicit search/test split isolation.
- Frontier mode improves reproducibility of candidate selection in repeated trials.
- Existing coding-tool benchmarks still run unchanged in default mode.
- A Claude Code backend can propose against the same coding-tool benchmarks as Codex.
- A Harbor adapter can score a candidate on a published Terminal-Bench subset without leaking held-out task names into proposer context.
