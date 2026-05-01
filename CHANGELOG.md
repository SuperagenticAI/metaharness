# Changelog

All notable changes to this project will be documented in this file.

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
