# Alignment With Official Meta-Harness

This page documents how `metaharness` aligns with the official Stanford IRIS Meta-Harness release while preserving the current strengths of this repository.

## Current Position

The official repository is the canonical research reference with:

- broad domain onboarding via `ONBOARDING.md`
- paper reference experiments
- domain-specific outer loops

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

## Main Gaps To Close

- Domain onboarding is not yet a first-class flow.
- Search-set and held-out test-set evaluation are not separated as first-class stages.
- Multi-candidate iteration and frontier policies are limited.
- Multi-objective selection policies are limited.
- Provider telemetry can be richer for research-grade analysis.

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

1. Stabilize onboarding command and docs.
2. Introduce adapter interfaces behind feature flags.
3. Add split evaluation support for one built-in example benchmark.
4. Add optional frontier mode with one reference policy.
5. Expand telemetry schemas and reporting.

## Risks And Mitigations

- Risk: overfitting core API to one research example.
- Mitigation: keep interfaces domain-agnostic and adapter-based.

- Risk: breaking current coding-tool user workflows.
- Mitigation: preserve existing commands and semantics as defaults.

- Risk: complexity jump in CLI and run layout.
- Mitigation: gate advanced modes behind explicit flags and document layouts clearly.

## Success Criteria

- A new domain can be scoped using onboarding files before any code changes.
- At least one adapter can run with explicit search/test split isolation.
- Frontier mode improves reproducibility of candidate selection in repeated trials.
- Existing coding-tool benchmarks still run unchanged in default mode.
