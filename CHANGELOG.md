# Changelog

All notable changes to this project will be documented in this file.

## [0.2.0] - 2026-04-15

### Added
- **Plugin Extension System**: Backend plugins via `backend_plugins` in metaharness.json with dynamic factory loading (`src/metaharness/extensions.py`)
- **Minimal Plugin Example**: Ready-to-use plugin example in `examples/minimal_plugin` demonstrating the factory contract
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

### Fixed
- Tests passing: 38 passed, 1 skipped

## [0.1.3] - 2026-04-14

### Added
- Initial release with Codex, Gemini, Pi, and OpenCode backends
- Basic optimization engine
- Filesystem-backed run store
- Experiment runner