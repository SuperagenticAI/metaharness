from __future__ import annotations

import json
import shutil
from difflib import unified_diff
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..bootstrap import EnvironmentBootstrap
from ..models import (
    AgentInstructions,
    CandidateRecord,
    ProposalRequest,
    ProposalResult,
)
from ..proposer.instructions import build_backend_prompt, render_backend_instructions

CHANGE_MANIFEST_SCHEMA_VERSION = "metaharness.change_manifest.v1"
_PASS_STATUSES = {"pass", "passed", "ok", "success", "true", "1"}


class FilesystemRunStore:
    def __init__(self, run_dir: Path) -> None:
        self.run_dir = run_dir
        self.run_id = run_dir.name
        self.candidates_dir = run_dir / "candidates"
        self.index_dir = run_dir / "indexes"

    def initialize_run(self, config: dict[str, Any]) -> None:
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.candidates_dir.mkdir(parents=True, exist_ok=True)
        self.index_dir.mkdir(parents=True, exist_ok=True)
        payload = dict(config)
        payload.setdefault("started_at", datetime.now(UTC).isoformat())
        self._write_json(self.run_dir / "run_config.json", payload)

    def materialize_baseline(self, baseline_workspace: Path) -> CandidateRecord:
        return self._materialize_candidate(
            candidate_id="c0000",
            parent_candidate_ids=[],
            source_workspace=baseline_workspace,
        )

    def materialize_candidate(self, parent: CandidateRecord) -> CandidateRecord:
        next_id = f"c{self._next_candidate_index():04d}"
        return self._materialize_candidate(
            candidate_id=next_id,
            parent_candidate_ids=[parent.candidate_id],
            source_workspace=parent.workspace_dir,
        )

    def _next_candidate_index(self) -> int:
        ids = [path.name for path in self.candidates_dir.iterdir() if path.is_dir()]
        if not ids:
            return 0
        return max(int(name[1:]) for name in ids) + 1

    def _materialize_candidate(
        self,
        candidate_id: str,
        parent_candidate_ids: list[str],
        source_workspace: Path,
    ) -> CandidateRecord:
        candidate_dir = self.candidates_dir / candidate_id
        workspace_dir = candidate_dir / "workspace"
        if candidate_dir.exists():
            shutil.rmtree(candidate_dir)
        candidate_dir.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source_workspace, workspace_dir)
        return CandidateRecord(
            candidate_id=candidate_id,
            parent_candidate_ids=parent_candidate_ids,
            candidate_dir=candidate_dir,
            workspace_dir=workspace_dir,
            manifest_path=candidate_dir / "manifest.json",
        )

    def write_instruction_bundle(
        self,
        candidate: CandidateRecord,
        parent: CandidateRecord,
        instructions: AgentInstructions,
        proposer_name: str,
        bootstrap: EnvironmentBootstrap,
        trace_evidence_path: Path | None = None,
    ) -> ProposalRequest:
        meta_dir = candidate.workspace_dir / ".metaharness"
        meta_dir.mkdir(parents=True, exist_ok=True)
        experience_dir = meta_dir / "experience"
        experience_dir.mkdir(parents=True, exist_ok=True)
        self._copy_parent_artifacts(parent, experience_dir / "parent")
        bootstrap_dir = meta_dir / "bootstrap"
        bootstrap_dir.mkdir(parents=True, exist_ok=True)
        bootstrap_summary_path = bootstrap_dir / "summary.md"
        bootstrap_snapshot_path = bootstrap_dir / "snapshot.json"
        bootstrap_summary_path.write_text(bootstrap.summary_text, encoding="utf-8")
        self._write_json(bootstrap_snapshot_path, bootstrap.snapshot)

        evidence_dir = meta_dir / "evidence"
        evidence_dir.mkdir(parents=True, exist_ok=True)
        candidate_trace_evidence_path: Path | None = None
        trace_evidence_text = ""
        if trace_evidence_path is not None:
            source = trace_evidence_path.resolve()
            if not source.exists():
                raise FileNotFoundError(f"trace evidence file not found: {source}")
            candidate_trace_evidence_path = evidence_dir / "trace_evidence.md"
            trace_evidence_text = source.read_text(encoding="utf-8")
            candidate_trace_evidence_path.write_text(trace_evidence_text, encoding="utf-8")

        parent_summary = {
            "parent_candidate_id": parent.candidate_id,
            "parent_objective": parent.objective,
            "constraints": instructions.constraints,
        }
        self._write_json(experience_dir / "parent_summary.json", parent_summary)

        instructions_path = meta_dir / self._instructions_filename(proposer_name)
        instructions_text = render_backend_instructions(proposer_name, instructions)
        instructions_path.write_text(instructions_text, encoding="utf-8")

        prompt_path = candidate.candidate_dir / "proposal" / "prompt.txt"
        prompt_path.parent.mkdir(parents=True, exist_ok=True)
        prompt_path.write_text(
            build_backend_prompt(
                proposer_name=proposer_name,
                instructions_path=instructions_path,
                workspace_dir=candidate.workspace_dir,
                bootstrap_summary_path=bootstrap_summary_path,
                bootstrap_summary_text=bootstrap.summary_text,
                trace_evidence_path=candidate_trace_evidence_path,
                trace_evidence_text=trace_evidence_text,
            ),
            encoding="utf-8",
        )

        return ProposalRequest(
            run_id=self.run_id,
            candidate_id=candidate.candidate_id,
            workspace_dir=candidate.workspace_dir,
            candidate_dir=candidate.candidate_dir,
            experience_dir=experience_dir,
            bootstrap_dir=bootstrap_dir,
            bootstrap_summary_path=bootstrap_summary_path,
            bootstrap_snapshot_path=bootstrap_snapshot_path,
            bootstrap_summary_text=bootstrap.summary_text,
            evidence_dir=evidence_dir,
            trace_evidence_path=candidate_trace_evidence_path,
            trace_evidence_text=trace_evidence_text,
            instructions_path=instructions_path,
            prompt_path=prompt_path,
            instructions=instructions,
            parent_candidate_ids=candidate.parent_candidate_ids,
        )

    def write_proposal_result(self, candidate_id: str, result: ProposalResult) -> None:
        proposal_dir = self.candidates_dir / candidate_id / "proposal"
        proposal_dir.mkdir(parents=True, exist_ok=True)
        self._write_json(proposal_dir / "result.json", result.to_dict())
        self._write_json(
            proposal_dir / "events.json",
            [event.to_dict() for event in result.events],
        )

    def capture_change_manifest(self, candidate: CandidateRecord) -> dict[str, Any]:
        source = candidate.workspace_dir / ".metaharness" / "change_manifest.json"
        proposal_dir = candidate.candidate_dir / "proposal"
        proposal_dir.mkdir(parents=True, exist_ok=True)
        canonical_path = proposal_dir / "change_manifest.json"

        manifest, valid, warnings = self._load_change_manifest(
            source=source,
            candidate=candidate,
        )
        manifest["validation"] = {
            "valid": valid,
            "warnings": warnings,
            "source_path": str(source),
        }
        self._write_json(canonical_path, manifest)

        changes = manifest.get("changes", [])
        components = sorted(
            {
                str(change.get("component", "")).strip()
                for change in changes
                if isinstance(change, dict) and str(change.get("component", "")).strip()
            }
        )
        predicted_fixes = sorted(
            {
                task
                for change in changes
                if isinstance(change, dict)
                for task in self._string_list(change.get("predicted_fixes"))
            }
        )
        risk_tasks = sorted(
            {
                task
                for change in changes
                if isinstance(change, dict)
                for task in self._string_list(change.get("risk_tasks"))
            }
        )

        candidate.change_manifest_valid = valid
        candidate.change_manifest_change_count = len(changes) if isinstance(changes, list) else 0
        candidate.change_manifest_components = components
        return {
            "change_manifest_path": str(canonical_path),
            "change_manifest_valid": valid,
            "change_manifest_warnings": warnings,
            "change_manifest_change_count": candidate.change_manifest_change_count,
            "change_manifest_components": components,
            "change_manifest_predicted_fixes": predicted_fixes,
            "change_manifest_risk_tasks": risk_tasks,
        }

    def write_validation_result(self, candidate_id: str, result: Any) -> None:
        self._write_json(self.candidates_dir / candidate_id / "validation" / "result.json", result.to_dict())

    def write_evaluation_result(self, candidate_id: str, result: Any) -> None:
        # Backward-compatible alias to search evaluation.
        self.write_search_evaluation_result(candidate_id, result)

    def write_search_evaluation_result(self, candidate_id: str, result: Any) -> None:
        evaluation_dir = self.candidates_dir / candidate_id / "evaluation"
        self._write_json(evaluation_dir / "result.json", result.to_dict())
        self._write_json(evaluation_dir / "search_result.json", result.to_dict())

    def write_change_attribution(
        self,
        parent: CandidateRecord,
        candidate: CandidateRecord,
        candidate_evaluation: Any,
    ) -> dict[str, Any]:
        manifest_path = candidate.candidate_dir / "proposal" / "change_manifest.json"
        parent_eval_path = parent.candidate_dir / "evaluation" / "search_result.json"
        if not manifest_path.exists() or not parent_eval_path.exists():
            return {}

        manifest = self._read_json(manifest_path)
        parent_eval = self._read_json(parent_eval_path)
        candidate_eval = candidate_evaluation.to_dict()
        parent_tasks = self._task_results_from_evaluation(parent_eval)
        candidate_tasks = self._task_results_from_evaluation(candidate_eval)
        if not parent_tasks or not candidate_tasks:
            return {}

        common_tasks = sorted(set(parent_tasks) & set(candidate_tasks))
        fixed = [
            task
            for task in common_tasks
            if parent_tasks[task] != "pass" and candidate_tasks[task] == "pass"
        ]
        regressed = [
            task
            for task in common_tasks
            if parent_tasks[task] == "pass" and candidate_tasks[task] != "pass"
        ]
        changed = fixed + regressed
        evaluations = []
        all_predicted: set[str] = set()
        all_risk: set[str] = set()

        for change in manifest.get("changes", []):
            if not isinstance(change, dict):
                continue
            predicted = self._string_list(change.get("predicted_fixes"))
            risks = self._string_list(change.get("risk_tasks"))
            all_predicted.update(predicted)
            all_risk.update(risks)
            actually_fixed = sorted(set(predicted) & set(fixed))
            still_failed = sorted(
                task
                for task in predicted
                if task in candidate_tasks and candidate_tasks[task] != "pass"
            )
            risk_realized = sorted(set(risks) & set(regressed))
            evaluations.append(
                {
                    "change_id": str(change.get("id", "unknown")),
                    "description": str(change.get("description", "")),
                    "component": str(change.get("component", "")),
                    "files": self._string_list(change.get("files")),
                    "predicted_fixes": predicted,
                    "actually_fixed": actually_fixed,
                    "still_failed": still_failed,
                    "risk_tasks": risks,
                    "risk_realized": risk_realized,
                    "hit_rate": f"{len(actually_fixed)}/{len(predicted)}" if predicted else "0/0",
                    "verdict": self._change_verdict(
                        predicted_count=len(predicted),
                        fixed_count=len(actually_fixed),
                        risk_count=len(risk_realized),
                    ),
                }
            )

        unattributed_regressions = sorted(set(regressed) - all_predicted - all_risk)
        verdict_counts: dict[str, int] = {}
        for evaluation in evaluations:
            verdict = str(evaluation["verdict"])
            verdict_counts[verdict] = verdict_counts.get(verdict, 0) + 1
        summary = ", ".join(f"{key}:{verdict_counts[key]}" for key in sorted(verdict_counts))
        attribution = {
            "schema_version": "metaharness.change_attribution.v1",
            "candidate_id": candidate.candidate_id,
            "parent_candidate_ids": candidate.parent_candidate_ids,
            "task_delta": {
                "fixed": sorted(fixed),
                "regressed": sorted(regressed),
                "changed": sorted(changed),
            },
            "change_evaluations": evaluations,
            "unattributed_regressions": unattributed_regressions,
            "verdict_counts": verdict_counts,
            "summary": summary,
        }
        attribution_path = candidate.candidate_dir / "proposal" / "change_attribution.json"
        self._write_json(attribution_path, attribution)
        candidate.change_attribution_summary = summary
        candidate.change_attribution_verdict_counts = verdict_counts
        return {
            "change_attribution_path": str(attribution_path),
            "change_attribution_summary": summary,
            "change_attribution_verdict_counts": verdict_counts,
        }

    def write_test_evaluation_result(self, candidate_id: str, result: Any) -> None:
        self._write_json(
            self.candidates_dir / candidate_id / "evaluation" / "test_result.json",
            result.to_dict(),
        )

    def write_candidate_manifest(self, candidate: CandidateRecord) -> None:
        self._write_json(
            candidate.manifest_path,
            {
                "candidate_id": candidate.candidate_id,
                "parent_candidate_ids": candidate.parent_candidate_ids,
                "objective": candidate.objective,
                "search_objective": candidate.search_objective,
                "test_objective": candidate.test_objective,
                "search_metrics": candidate.search_metrics,
                "test_metrics": candidate.test_metrics,
                "valid": candidate.valid,
                "test_valid": candidate.test_valid,
                "proposal_applied": candidate.proposal_applied,
                "outcome": candidate.outcome,
                "outcome_summary": candidate.outcome_summary,
                "scope_violation_paths": candidate.scope_violation_paths,
                "frontier_rank": candidate.frontier_rank,
                "change_manifest_valid": candidate.change_manifest_valid,
                "change_manifest_change_count": candidate.change_manifest_change_count,
                "change_manifest_components": candidate.change_manifest_components,
                "change_attribution_summary": candidate.change_attribution_summary,
                "change_attribution_verdict_counts": candidate.change_attribution_verdict_counts,
                "workspace_dir": str(candidate.workspace_dir),
                "updated_at": datetime.now(UTC).isoformat(),
            },
        )

    def write_index(self, data: dict[str, Any]) -> None:
        self._write_json(self.index_dir / "leaderboard.json", data)

    def capture_workspace_diff(self, parent: CandidateRecord, candidate: CandidateRecord) -> dict[str, Any]:
        proposal_dir = candidate.candidate_dir / "proposal"
        proposal_dir.mkdir(parents=True, exist_ok=True)
        changes: list[dict[str, str]] = []
        rendered_diffs: list[str] = []

        parent_files = self._workspace_file_map(parent.workspace_dir)
        candidate_files = self._workspace_file_map(candidate.workspace_dir)
        for relative_path in sorted(set(parent_files) | set(candidate_files)):
            before = parent_files.get(relative_path)
            after = candidate_files.get(relative_path)
            if before is None and after is not None:
                changes.append({"path": relative_path, "kind": "added"})
                rendered_diffs.append(self._render_file_diff(relative_path, None, after))
            elif before is not None and after is None:
                changes.append({"path": relative_path, "kind": "deleted"})
                rendered_diffs.append(self._render_file_diff(relative_path, before, None))
            elif before is not None and after is not None and before != after:
                changes.append({"path": relative_path, "kind": "modified"})
                rendered_diffs.append(self._render_file_diff(relative_path, before, after))

        diff_path = proposal_dir / "workspace.diff"
        changes_path = proposal_dir / "workspace_changes.json"
        diff_path.write_text("".join(rendered_diffs), encoding="utf-8")
        self._write_json(changes_path, changes)
        return {
            "workspace_diff_path": str(diff_path),
            "workspace_changes_path": str(changes_path),
            "workspace_changed_files": [item["path"] for item in changes],
            "workspace_change_count": len(changes),
        }

    def _write_json(self, path: Path, data: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        loaded = json.loads(path.read_text(encoding="utf-8"))
        return loaded if isinstance(loaded, dict) else {}

    def _load_change_manifest(
        self,
        *,
        source: Path,
        candidate: CandidateRecord,
    ) -> tuple[dict[str, Any], bool, list[str]]:
        warnings: list[str] = []
        raw: dict[str, Any]
        if not source.exists():
            warnings.append("missing .metaharness/change_manifest.json")
            raw = {}
        else:
            try:
                loaded = json.loads(source.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                warnings.append(f"invalid JSON: {exc}")
                loaded = {}
            raw = loaded if isinstance(loaded, dict) else {}
            if not isinstance(loaded, dict):
                warnings.append("manifest root must be a JSON object")

        changes_raw = raw.get("changes", [])
        if not isinstance(changes_raw, list):
            warnings.append("changes must be a list")
            changes_raw = []

        changes = []
        for index, change in enumerate(changes_raw):
            if not isinstance(change, dict):
                warnings.append(f"changes[{index}] must be an object")
                continue
            change_id = str(change.get("id") or f"change-{index + 1}")
            component = str(change.get("component", change.get("component_level", ""))).strip()
            if not component:
                warnings.append(f"{change_id}: component is required")
            files = self._string_list(change.get("files"))
            if not files:
                warnings.append(f"{change_id}: files should list touched harness files")
            changes.append(
                {
                    "id": change_id,
                    "component": component,
                    "description": str(change.get("description", "")),
                    "files": files,
                    "failure_pattern": str(change.get("failure_pattern", "")),
                    "evidence_refs": self._string_list(change.get("evidence_refs")),
                    "root_cause": str(change.get("root_cause", "")),
                    "targeted_fix": str(change.get("targeted_fix", "")),
                    "predicted_fixes": self._string_list(change.get("predicted_fixes")),
                    "risk_tasks": self._string_list(change.get("risk_tasks")),
                    "notes": str(change.get("notes", "")),
                }
            )

        manifest = {
            "schema_version": str(raw.get("schema_version") or CHANGE_MANIFEST_SCHEMA_VERSION),
            "candidate_id": str(raw.get("candidate_id") or candidate.candidate_id),
            "parent_candidate_ids": self._string_list(
                raw.get("parent_candidate_ids") or candidate.parent_candidate_ids
            ),
            "changes": changes,
        }
        if manifest["candidate_id"] != candidate.candidate_id:
            warnings.append(
                f"candidate_id mismatch: manifest has {manifest['candidate_id']}, expected {candidate.candidate_id}"
            )
        return manifest, not warnings, warnings

    @staticmethod
    def _string_list(value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item) for item in value if str(item).strip()]
        if isinstance(value, tuple | set):
            return [str(item) for item in value if str(item).strip()]
        text = str(value).strip()
        return [text] if text else []

    @staticmethod
    def _task_results_from_evaluation(evaluation: dict[str, Any]) -> dict[str, str]:
        metadata = evaluation.get("metadata", {})
        task_results = None
        if isinstance(metadata, dict):
            task_results = metadata.get("task_results")
        if task_results is None:
            task_results = evaluation.get("task_results")
        if not isinstance(task_results, dict):
            return {}
        return {
            str(task): FilesystemRunStore._normalize_task_status(status)
            for task, status in task_results.items()
        }

    @staticmethod
    def _normalize_task_status(status: Any) -> str:
        if isinstance(status, bool):
            return "pass" if status else "fail"
        text = str(status).strip().lower()
        return "pass" if text in _PASS_STATUSES else "fail"

    @staticmethod
    def _change_verdict(*, predicted_count: int, fixed_count: int, risk_count: int) -> str:
        if risk_count > 0 and fixed_count == 0:
            return "HARMFUL"
        if risk_count > 0 and fixed_count > 0:
            return "MIXED"
        if predicted_count > 0 and fixed_count == predicted_count:
            return "EFFECTIVE"
        if fixed_count > 0:
            return "PARTIALLY_EFFECTIVE"
        return "INEFFECTIVE"

    def _copy_parent_artifacts(self, parent: CandidateRecord, target_dir: Path) -> None:
        target_dir.mkdir(parents=True, exist_ok=True)
        candidates_dir = parent.candidate_dir
        for relative in [
            Path("manifest.json"),
            Path("validation/result.json"),
            Path("evaluation/result.json"),
            Path("proposal/result.json"),
            Path("proposal/change_manifest.json"),
            Path("proposal/change_attribution.json"),
        ]:
            source = candidates_dir / relative
            if not source.exists():
                continue
            destination = target_dir / relative.name if relative.parent == Path(".") else target_dir / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)

    @staticmethod
    def _instructions_filename(proposer_name: str) -> str:
        if proposer_name == "codex":
            return "AGENTS.md"
        if proposer_name == "gemini":
            return "GEMINI.md"
        return "INSTRUCTIONS.md"

    @staticmethod
    def _workspace_file_map(workspace_dir: Path) -> dict[str, bytes]:
        files: dict[str, bytes] = {}
        for path in workspace_dir.rglob("*"):
            if not path.is_file():
                continue
            relative = path.relative_to(workspace_dir)
            if relative.parts and relative.parts[0] == ".metaharness":
                continue
            files[relative.as_posix()] = path.read_bytes()
        return files

    @staticmethod
    def _render_file_diff(relative_path: str, before: bytes | None, after: bytes | None) -> str:
        before_text = FilesystemRunStore._decode_for_diff(before)
        after_text = FilesystemRunStore._decode_for_diff(after)
        if before_text is None or after_text is None:
            before_size = 0 if before is None else len(before)
            after_size = 0 if after is None else len(after)
            return (
                f"Binary change {relative_path}: "
                f"{before_size} bytes -> {after_size} bytes\n"
            )

        return "".join(
            unified_diff(
                before_text.splitlines(keepends=True),
                after_text.splitlines(keepends=True),
                fromfile=f"a/{relative_path}",
                tofile=f"b/{relative_path}",
            )
        )

    @staticmethod
    def _decode_for_diff(content: bytes | None) -> str | None:
        if content is None:
            return ""
        try:
            return content.decode("utf-8")
        except UnicodeDecodeError:
            return None
