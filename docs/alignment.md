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

## Phased Plan

1. Phase 1: Domain Onboarding Surface
- Add an official-style onboarding entry point.
- Output a structured `domain_spec.md` for new domain work.
- Status: started. `metaharness onboard <target_dir>` now writes `ONBOARDING.md` and `domain_spec.md`.
  Status: implemented.

2. Phase 2: Domain Adapter API
- Generalize current coding-tool integration into a domain adapter contract.
- Keep coding-tool adapter as the default built-in implementation.
- Define adapter hooks for validation, search evaluation, and optional test evaluation.
  Status: implemented with backward-compatible wrapping of legacy validator/evaluator pairs.

3. Phase 3: Split Evaluation Model
- Add explicit search-stage versus held-out test-stage evaluation.
- Ensure test-stage artifacts are never leaked to proposer context during search.
- Add run metadata fields that record split definitions and leakage safeguards.
  Status: implemented in engine/store with `search_result.json` and optional `test_result.json`.

4. Phase 4: Frontier and Multi-Candidate Search
- Add optional batch candidate proposals per iteration.
- Add frontier policies beyond single scalar best, including Pareto-style policies.
- Keep simple hill-climb mode as the default for low-cost workflows.
  Status: implemented with `search_mode`, `proposal_batch_size`, and `selection_policy`.

5. Phase 5: Telemetry and Experiment Upgrades
- Extend proposal telemetry with token, cost, and tool-level summaries where available.
- Add richer experiment summary outputs for multi-objective comparisons.
- Keep current `inspect`, `ledger`, `summarize`, and `experiment` outputs backward compatible where possible.
  Status: implemented with token/tool/cost fields and expanded trial/summary columns.

## Near-Term Implementation Sequence

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
