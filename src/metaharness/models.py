from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class AgentEvent:
    ts: str | None
    kind: str
    text: str | None = None
    command: str | None = None
    output: str | None = None
    file_changes: list[str] = field(default_factory=list)
    tool_name: str | None = None
    raw: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class AgentInstructions:
    objective: str
    constraints: list[str] = field(default_factory=list)
    workspace_layout: str = ""
    allowed_actions: list[str] = field(default_factory=list)
    forbidden_actions: list[str] = field(default_factory=list)
    evaluation_contract: str = ""


@dataclass(slots=True)
class ProposalRequest:
    run_id: str
    candidate_id: str
    workspace_dir: Path
    candidate_dir: Path
    experience_dir: Path
    bootstrap_dir: Path
    bootstrap_summary_path: Path
    bootstrap_snapshot_path: Path
    bootstrap_summary_text: str
    evidence_dir: Path
    trace_evidence_path: Path | None
    trace_evidence_text: str
    instructions_path: Path
    prompt_path: Path
    instructions: AgentInstructions
    parent_candidate_ids: list[str]


@dataclass(slots=True)
class ProposalExecution:
    command: list[str]
    cwd: Path
    stdout_path: Path
    stderr_path: Path
    last_message_path: Path | None = None
    returncode: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ProposalResult:
    applied: bool
    summary: str
    final_text: str = ""
    changed_files: list[str] = field(default_factory=list)
    events: list[AgentEvent] = field(default_factory=list)
    raw_stdout_path: Path | None = None
    raw_stderr_path: Path | None = None
    token_usage: dict[str, int] = field(default_factory=dict)
    cost_usd: float | None = None
    files_read: dict[str, dict[str, int]] = field(default_factory=dict)
    files_written: dict[str, dict[str, int]] = field(default_factory=dict)
    tool_call_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["raw_stdout_path"] = str(self.raw_stdout_path) if self.raw_stdout_path else None
        data["raw_stderr_path"] = str(self.raw_stderr_path) if self.raw_stderr_path else None
        return data


@dataclass(slots=True)
class ValidationResult:
    ok: bool
    summary: str
    metrics: dict[str, float] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class EvaluationResult:
    objective: float
    metrics: dict[str, float] = field(default_factory=dict)
    summary: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class CandidateRecord:
    candidate_id: str
    parent_candidate_ids: list[str]
    candidate_dir: Path
    workspace_dir: Path
    manifest_path: Path
    objective: float | None = None
    search_objective: float | None = None
    test_objective: float | None = None
    search_metrics: dict[str, float] = field(default_factory=dict)
    test_metrics: dict[str, float] = field(default_factory=dict)
    valid: bool = False
    test_valid: bool | None = None
    proposal_applied: bool = False
    outcome: str = "unknown"
    outcome_summary: str = ""
    scope_violation_paths: list[str] = field(default_factory=list)
    frontier_rank: int | None = None
    change_manifest_valid: bool | None = None
    change_manifest_change_count: int = 0
    change_manifest_components: list[str] = field(default_factory=list)
    change_attribution_summary: str = ""
    change_attribution_verdict_counts: dict[str, int] = field(default_factory=dict)


@dataclass(slots=True)
class OptimizeResult:
    run_dir: Path
    run_id: str
    best_candidate_id: str
    best_workspace_dir: Path
    best_objective: float
    candidate_ids: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_dir": str(self.run_dir),
            "run_id": self.run_id,
            "best_candidate_id": self.best_candidate_id,
            "best_workspace_dir": str(self.best_workspace_dir),
            "best_objective": self.best_objective,
            "candidate_ids": list(self.candidate_ids),
        }
