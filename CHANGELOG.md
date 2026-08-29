# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

## [0.6.0] - 2026-08-29

### Added
- Leakage gate rejects candidate diffs that copy task IDs, test names, or other forbidden evaluation tokens into harness files (`leakage_gate`, outcome `leakage-violation`).
- Write-scope classes on `allowed_write_paths` (`prompt`, `skill`, `middleware`, and related) with optional `write_scope_mode: "single-class"` (outcome `class-violation`).
- `skills` scaffold profile that seeds a shared Agent Skill under `.agents/skills`, plus Claude/Gemini skill directories, `@AGENTS.md` imports, and held-out `test_tasks.json`.

### Changed
- Official comparison and alignment docs now cover the July 2026 Harbor meta-harness pilot, Harness Forge, HarnessCompass, and the Wang et al. harness-evolution eval critique.
- Official comparison no longer lists Pi and OpenCode as current backends. Those were removed in 0.2.0. Current experimental backends are Gemini CLI and Omnigent.
- Filled empty reference links on the official comparison page.

## [0.5.0] - 2026-08-23

### Changed
- Relicensed from Apache-2.0 to the Functional Source License, Version 1.1,
  ALv2 Future License (`FSL-1.1-ALv2`). The source stays public to read, use,
  modify and redistribute for any Permitted Purpose; only a Competing Use is
  excluded. Each release converts to Apache-2.0 on the second anniversary of
  its publication.
- Releases up to and including `0.4.0` were published under Apache-2.0 and
  remain available under those terms.
- The previous Apache-2.0 text is preserved at `LICENSE-APACHE-2.0`, which is
  also the Future License this project converts to.

### Fixed
- `examples/omnigent_agent_benchmark/runs/` is now ignored, matching the other
  example benchmark directories.

## [0.4.0] - 2026-06-13

### Added
- Experimental `OmnigentCliBackend` proposer backend for running candidate proposals through `omni run`.
- Per-candidate generated Omnigent agent bundles under `.metaharness/omnigent_agent/config.yaml`, with copies archived at `proposal/omnigent_agent.yaml`.
- Mapping from `allowed_write_paths` into generated Omnigent sandbox write paths and a `metaharness_enforce_sandbox` policy.
- Omnigent event parsing for JSON, JSONL, and SSE-style streams, with normalized proposal events, final text, changed files, token usage, tool-call count, cost, and file read/write telemetry.
- Example Omnigent-agent optimization benchmark at `examples/omnigent_agent_benchmark`.
- Real Omnigent smoke coverage proving the backend can improve an Omnigent agent candidate: `best_candidate_id=c0001`, `best_objective=0.875`, and no scope violations in the verified run.

### Changed
- Coding-tool backend configuration now accepts `backend: "omnigent"` with Omnigent CLI options.
- Candidate proposal requests now carry `allowed_write_paths` so proposer backends can enforce or translate write scope earlier.
- Omnigent-generated instruction files use `AGENTS.md` to match Omnigent and Codex conventions.
- Provider docs now document Omnigent setup, generated agent config, telemetry import, and practical backend selection guidance.

### Fixed
- Omnigent backend now pins generated agent `os_env.cwd` to the absolute candidate workspace, avoiding accidental execution relative to the generated agent bundle.
- Omnigent/Codex private `.codex-tmp` runtime scratch is cleaned before metaharness computes diffs and write-scope violations.
- Omnigent result extraction now prefers useful proposal stdout over startup warnings emitted on stderr.

## [0.3.0] - 2026-05-26

### Added
- Paper-aligned filesystem experience snapshots that expose prior candidate workspaces, manifests, search scores, proposal traces, diffs, and attribution artifacts to later proposers.
- Run-level Pareto frontier output at `indexes/frontier.json` plus `OptimizeResult.frontier_candidate_ids`.
- Held-out test evaluation finalization for the selected frontier after search completes.
- Paper-like `python_fixture_benchmark` defaults with frontier search, batched proposals, Pareto selection, and `test_tasks.json`.
- Checked-in hosted Codex paper-like experiment config at `examples/experiment_configs/codex-paperlike-fixture.json`.
- Normalized coding-tool evaluator `task_results` metadata for change attribution.
- Experiment config `project_overrides` for search mode, proposal batch size, and selection policy.

### Changed
- Proposal prompts now direct Codex/Gemini to compare all prior candidates, not only the immediate parent.
- Legacy evaluator wrapping now honors `evaluate_search` and `evaluate_test` methods when present.

## [0.2.2] - 2026-05-01

### Added
- AHE-style decision observability with `.metaharness/change_manifest.json`, archived candidate manifests, optional task-level change attribution, and ledger fields for components/verdicts.

## [0.2.1] - 2026-04-30

### Added
- Trace evidence injection for candidate proposals via `--trace-evidence`, `optimize_harness(trace_evidence_path=...)`, and `run_coding_tool_project(trace_evidence_path=...)`.
- Candidate workspaces now receive `.metaharness/evidence/trace_evidence.md` when trace evidence is supplied.
- Proposal prompts now explicitly reference and embed supplied trace evidence so Codex/Gemini can ground harness edits in observed failures.

## [0.2.0] - 2026-04-15

### Added
- **Plugin Extension System**: Backend plugins via `backend_plugins` in metaharness.json with dynamic factory loading
- **Domain Adapter & Split Eval**: Domain adapter for custom evaluation and split frontier controls for cost-aware selection
- **Telemetry Expansion**: Enhanced reporting with token usage, cost tracking, and file-level telemetry
- **Documentation**: Official alignment docs (`docs/alignment.md`, `docs/official-comparison.md`)

### Removed
- **Pi Backend**: Removed Pi CLI backend and parser
- **OpenCode Backend**: Removed OpenCode backend and parser

### Changed
- **Architecture Refactor**: Core engine now supports frontier-based selection with cost-aware Pareto optimization
- **CLI Simplification**: Streamlined command interface
- **Provider Focus**: Codex-first with Gemini as experimental backend

## [0.1.3] - 2026-04-14

### Added
- Initial release with Codex, Gemini, Pi, and OpenCode backends
- Basic optimization engine
- Filesystem-backed run store
- Experiment runner
