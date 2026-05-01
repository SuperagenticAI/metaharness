from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Sequence

from ..bootstrap import collect_environment_bootstrap
from ..domain import DomainAdapterProtocol
from ..models import (
    AgentInstructions,
    CandidateRecord,
    OptimizeResult,
)
from ..proposer.base import ProposerBackend
from ..store.filesystem import FilesystemRunStore


class MetaHarnessEngine:
    def __init__(
        self,
        baseline: Path,
        proposer: ProposerBackend,
        domain_adapter: DomainAdapterProtocol,
        run_dir: Path,
        budget: int,
        objective: str,
        constraints: Sequence[str] | None = None,
        allowed_write_paths: Sequence[str] | None = None,
        trace_evidence_path: Path | None = None,
        search_mode: str = "hill-climb",
        proposal_batch_size: int = 1,
        selection_policy: str = "single",
    ) -> None:
        self.baseline = baseline.resolve()
        self.proposer = proposer
        self.domain_adapter = domain_adapter
        self.run_dir = run_dir.resolve()
        self.budget = budget
        self.objective = objective
        self.constraints = list(constraints or [])
        self.allowed_write_paths = [self._normalize_allowed_path(value) for value in (allowed_write_paths or []) if str(value).strip()]
        self.trace_evidence_path = trace_evidence_path.resolve() if trace_evidence_path is not None else None
        self.search_mode = search_mode
        self.proposal_batch_size = max(1, int(proposal_batch_size))
        self.selection_policy = selection_policy
        if self.search_mode not in {"hill-climb", "frontier"}:
            raise ValueError(f"unsupported search_mode: {self.search_mode}")
        if self.selection_policy not in {"single", "pareto"}:
            raise ValueError(f"unsupported selection_policy: {self.selection_policy}")
        self.store = FilesystemRunStore(self.run_dir)

    def _build_instructions(self, parent: CandidateRecord) -> AgentInstructions:
        return AgentInstructions(
            objective=self.objective,
            constraints=self._instruction_constraints(),
            workspace_layout=(
                "The candidate workspace is the directory under optimization. "
                "The .metaharness directory contains run metadata, a compact environment bootstrap, "
                "and prior results."
            ),
            allowed_actions=[
                "Read and edit files inside the candidate workspace.",
                "Use the bootstrap snapshot under .metaharness/bootstrap to avoid redundant exploration.",
                "Inspect prior candidate artifacts under .metaharness.",
                "Use lightweight commands when needed to understand the workspace.",
            ],
            forbidden_actions=[
                "Do not modify evaluation artifacts outside the current candidate workspace.",
                *self._write_scope_forbidden_actions(),
                "Do not fabricate success. The external validator and evaluator decide outcomes.",
            ],
            evaluation_contract=(
                "Your job is to improve the harness so that external validation passes and the "
                "objective score increases relative to the parent candidate "
                f"({parent.candidate_id})."
            ),
        )

    def run(self) -> OptimizeResult:
        self.store.initialize_run(
            {
                "objective": self.objective,
                "constraints": self.constraints,
                "budget": self.budget,
                "proposer": self.proposer.name,
                "baseline": str(self.baseline),
                "allowed_write_paths": self.allowed_write_paths,
                "trace_evidence_path": str(self.trace_evidence_path) if self.trace_evidence_path else None,
                "search_mode": self.search_mode,
                "proposal_batch_size": self.proposal_batch_size,
                "selection_policy": self.selection_policy,
            }
        )

        baseline = self.store.materialize_baseline(self.baseline)
        baseline.proposal_applied = True
        baseline_validation = self.domain_adapter.validate(baseline.workspace_dir)
        self.store.write_validation_result(baseline.candidate_id, baseline_validation)
        baseline.valid = baseline_validation.ok
        if baseline.valid:
            baseline_eval = self.domain_adapter.evaluate_search(baseline.workspace_dir)
            self.store.write_search_evaluation_result(baseline.candidate_id, baseline_eval)
            baseline.search_objective = baseline_eval.objective
            baseline.search_metrics = dict(baseline_eval.metrics)
            baseline.objective = baseline.search_objective
            baseline_test = self.domain_adapter.evaluate_test(baseline.workspace_dir)
            if baseline_test is not None:
                self.store.write_test_evaluation_result(baseline.candidate_id, baseline_test)
                baseline.test_valid = True
                baseline.test_objective = baseline_test.objective
                baseline.test_metrics = dict(baseline_test.metrics)
        else:
            baseline.search_objective = float("-inf")
            baseline.objective = float("-inf")
        baseline.outcome = "baseline"
        baseline.outcome_summary = "Baseline candidate."
        self.store.write_candidate_manifest(baseline)

        best = baseline
        candidates = [baseline.candidate_id]

        for _ in range(self.budget):
            parent = best
            batch = [
                self.store.materialize_candidate(parent)
                for _ in range(self._effective_batch_size())
            ]
            for candidate in batch:
                self._evaluate_candidate(parent=parent, candidate=candidate)
                self.store.write_candidate_manifest(candidate)
                candidates.append(candidate.candidate_id)

            selected = self._select_next_parent(parent=parent, batch=batch)
            if selected is not parent:
                selected.outcome = "keep"
                selected.outcome_summary = self._keep_summary(parent, selected)
                self.store.write_candidate_manifest(selected)
                best = selected
            for candidate in batch:
                if candidate.candidate_id == best.candidate_id:
                    continue
                if candidate.outcome in {"crash", "timeout", "scope-violation", "no-change"}:
                    continue
                if candidate.valid:
                    candidate.outcome = "discard"
                    candidate.outcome_summary = self._discard_summary(parent, candidate)
                    self.store.write_candidate_manifest(candidate)

        self.store.write_index(
            {
                "best_candidate_id": best.candidate_id,
                "best_objective": best.objective,
                "candidates": candidates,
                "completed_at": datetime.now(UTC).isoformat(),
            }
        )
        return OptimizeResult(
            run_dir=self.run_dir,
            run_id=self.store.run_id,
            best_candidate_id=best.candidate_id,
            best_workspace_dir=best.workspace_dir,
            best_objective=best.objective if best.objective is not None else float("-inf"),
            candidate_ids=candidates,
        )

    def _evaluate_candidate(self, parent: CandidateRecord, candidate: CandidateRecord) -> None:
        instructions = self._build_instructions(parent)
        bootstrap = collect_environment_bootstrap(candidate.workspace_dir)
        proposal_request = self.store.write_instruction_bundle(
            candidate=candidate,
            parent=parent,
            instructions=instructions,
            proposer_name=self.proposer.name,
            bootstrap=bootstrap,
            trace_evidence_path=self.trace_evidence_path,
        )
        execution = self.proposer.invoke(self.proposer.prepare(proposal_request))
        proposal_result = self.proposer.collect(execution)
        diff_metadata = self.store.capture_workspace_diff(parent=parent, candidate=candidate)
        change_manifest_metadata = self.store.capture_change_manifest(candidate)
        proposal_result.changed_files = sorted(
            set(proposal_result.changed_files) | set(diff_metadata["workspace_changed_files"])
        )
        proposal_result.metadata = {
            **proposal_result.metadata,
            "workspace_diff_path": diff_metadata["workspace_diff_path"],
            "workspace_changes_path": diff_metadata["workspace_changes_path"],
            "workspace_change_count": diff_metadata["workspace_change_count"],
            **change_manifest_metadata,
        }
        workspace_change_count = int(diff_metadata["workspace_change_count"])
        candidate.proposal_applied = proposal_result.applied
        self.store.write_proposal_result(candidate.candidate_id, proposal_result)

        if not proposal_result.applied:
            candidate.valid = False
            candidate.search_objective = float("-inf")
            candidate.objective = float("-inf")
            candidate.outcome = self._classify_failed_proposal(proposal_result)
            candidate.outcome_summary = proposal_result.summary
            return

        if violation_paths := self._scope_violations(proposal_result.changed_files):
            candidate.valid = False
            candidate.search_objective = float("-inf")
            candidate.objective = float("-inf")
            candidate.outcome = "scope-violation"
            candidate.scope_violation_paths = violation_paths
            candidate.outcome_summary = (
                "Changed files outside the allowed write scope: "
                + ", ".join(violation_paths)
            )
            return

        if workspace_change_count == 0:
            candidate.valid = parent.valid
            candidate.search_objective = parent.search_objective
            candidate.test_objective = parent.test_objective
            candidate.search_metrics = dict(parent.search_metrics)
            candidate.test_metrics = dict(parent.test_metrics)
            candidate.objective = parent.objective
            candidate.test_valid = parent.test_valid
            candidate.outcome = "no-change"
            candidate.outcome_summary = "No workspace changes detected relative to the parent candidate."
            return

        validation = self.domain_adapter.validate(candidate.workspace_dir)
        candidate.valid = validation.ok
        self.store.write_validation_result(candidate.candidate_id, validation)
        if not validation.ok:
            candidate.search_objective = float("-inf")
            candidate.objective = float("-inf")
            candidate.outcome = "discard"
            candidate.outcome_summary = validation.summary
            return

        search_eval = self.domain_adapter.evaluate_search(candidate.workspace_dir)
        self.store.write_search_evaluation_result(candidate.candidate_id, search_eval)
        self.store.write_change_attribution(parent=parent, candidate=candidate, candidate_evaluation=search_eval)
        candidate.search_objective = search_eval.objective
        candidate.search_metrics = dict(search_eval.metrics)
        candidate.objective = candidate.search_objective
        candidate.outcome = "unknown"
        candidate.outcome_summary = ""

        test_eval = self.domain_adapter.evaluate_test(candidate.workspace_dir)
        if test_eval is not None:
            self.store.write_test_evaluation_result(candidate.candidate_id, test_eval)
            candidate.test_valid = True
            candidate.test_objective = test_eval.objective
            candidate.test_metrics = dict(test_eval.metrics)

    def _effective_batch_size(self) -> int:
        if self.search_mode == "hill-climb":
            return self.proposal_batch_size
        return max(2, self.proposal_batch_size)

    def _select_next_parent(self, parent: CandidateRecord, batch: Sequence[CandidateRecord]) -> CandidateRecord:
        valid_improving = [
            candidate
            for candidate in batch
            if candidate.valid
            and candidate.search_objective is not None
            and (parent.search_objective is None or candidate.search_objective > parent.search_objective)
        ]
        if not valid_improving:
            return parent
        if self.selection_policy == "pareto":
            return self._select_pareto(valid_improving)
        return max(valid_improving, key=lambda c: c.search_objective if c.search_objective is not None else float("-inf"))

    def _select_pareto(self, candidates: Sequence[CandidateRecord]) -> CandidateRecord:
        points = []
        for candidate in candidates:
            score = candidate.search_objective if candidate.search_objective is not None else float("-inf")
            cost = self._secondary_cost(candidate)
            points.append((candidate, score, cost))

        frontier = []
        for candidate, score, cost in points:
            dominated = False
            for _, other_score, other_cost in points:
                if other_score >= score and other_cost <= cost and (other_score > score or other_cost < cost):
                    dominated = True
                    break
            if not dominated:
                frontier.append((candidate, score, cost))

        frontier.sort(key=lambda item: (item[1], -item[2]), reverse=True)
        for rank, (candidate, _, _) in enumerate(frontier, start=1):
            candidate.frontier_rank = rank
        return frontier[0][0]

    @staticmethod
    def _secondary_cost(candidate: CandidateRecord) -> float:
        for key in ("context_len", "context_chars", "context_cost", "prompt_len"):
            value = candidate.search_metrics.get(key)
            if value is not None:
                return float(value)
        return float("inf")

    @staticmethod
    def _classify_failed_proposal(result) -> str:
        if bool(result.metadata.get("timed_out")):
            return "timeout"
        return "crash"

    @staticmethod
    def _keep_summary(parent: CandidateRecord, candidate: CandidateRecord) -> str:
        return (
            "Objective improved from "
            f"{MetaHarnessEngine._format_objective(parent.objective)} to "
            f"{MetaHarnessEngine._format_objective(candidate.objective)}."
        )

    @staticmethod
    def _discard_summary(parent: CandidateRecord, candidate: CandidateRecord) -> str:
        return (
            "Objective "
            f"{MetaHarnessEngine._format_objective(candidate.objective)} did not improve over "
            f"{parent.candidate_id} ({MetaHarnessEngine._format_objective(parent.objective)})."
        )

    @staticmethod
    def _format_objective(value: float | None) -> str:
        if value is None:
            return "None"
        return f"{value:.3f}"

    def _instruction_constraints(self) -> list[str]:
        constraints = list(self.constraints)
        if self.allowed_write_paths:
            constraints.append(
                "Only modify files within the allowed write scope: "
                + ", ".join(self.allowed_write_paths)
            )
        return constraints

    def _write_scope_forbidden_actions(self) -> list[str]:
        if not self.allowed_write_paths:
            return []
        return [
            "Do not edit files outside the allowed write scope: "
            + ", ".join(self.allowed_write_paths)
        ]

    def _scope_violations(self, changed_files: Sequence[str]) -> list[str]:
        if not self.allowed_write_paths:
            return []
        violations: list[str] = []
        for path in changed_files:
            normalized_path = self._normalize_relative_path(path)
            if normalized_path is None:
                continue
            if not any(self._path_is_allowed(normalized_path, allowed) for allowed in self.allowed_write_paths):
                violations.append(normalized_path)
        return sorted(set(violations))

    @staticmethod
    def _path_is_allowed(path: str, allowed: str) -> bool:
        if allowed in {"*", "."}:
            return True
        if path == allowed:
            return True
        return path.startswith(f"{allowed}/")

    @staticmethod
    def _normalize_relative_path(value: str) -> str | None:
        text = str(value).replace("\\", "/").strip().strip("/")
        if not text or text in {".", ".."}:
            return None
        parts = [part for part in text.split("/") if part not in {"", "."}]
        if any(part == ".." for part in parts):
            return None
        return "/".join(parts)

    @classmethod
    def _normalize_allowed_path(cls, value: str) -> str:
        normalized = cls._normalize_relative_path(value)
        if normalized is None:
            return "."
        return normalized
