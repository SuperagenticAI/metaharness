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

    def write_validation_result(self, candidate_id: str, result: Any) -> None:
        self._write_json(self.candidates_dir / candidate_id / "validation" / "result.json", result.to_dict())

    def write_evaluation_result(self, candidate_id: str, result: Any) -> None:
        # Backward-compatible alias to search evaluation.
        self.write_search_evaluation_result(candidate_id, result)

    def write_search_evaluation_result(self, candidate_id: str, result: Any) -> None:
        evaluation_dir = self.candidates_dir / candidate_id / "evaluation"
        self._write_json(evaluation_dir / "result.json", result.to_dict())
        self._write_json(evaluation_dir / "search_result.json", result.to_dict())

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

    def _copy_parent_artifacts(self, parent: CandidateRecord, target_dir: Path) -> None:
        target_dir.mkdir(parents=True, exist_ok=True)
        candidates_dir = parent.candidate_dir
        for relative in [
            Path("manifest.json"),
            Path("validation/result.json"),
            Path("evaluation/result.json"),
            Path("proposal/result.json"),
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
