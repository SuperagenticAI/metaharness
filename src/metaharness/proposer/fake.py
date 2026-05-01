from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from typing import Any

from ..models import AgentEvent, ProposalExecution, ProposalRequest, ProposalResult
from .base import ProposerBackend


class FakeBackend(ProposerBackend):
    name = "fake"

    def __init__(self, mutation: Callable[[ProposalRequest], Mapping[str, Any]] | None = None) -> None:
        self.mutation = mutation or self._default_mutation

    def prepare(self, request: ProposalRequest) -> ProposalRequest:
        return request

    def invoke(self, request: ProposalRequest) -> ProposalExecution:
        proposal_dir = request.candidate_dir / "proposal"
        proposal_dir.mkdir(parents=True, exist_ok=True)
        stdout_path = proposal_dir / "stdout.jsonl"
        stderr_path = proposal_dir / "stderr.txt"

        outcome = dict(self.mutation(request))
        files = outcome.get("files")
        if isinstance(files, list) and files:
            for file_spec in files:
                if not isinstance(file_spec, Mapping):
                    continue
                self._apply_file_mutation(request, file_spec)
        else:
            self._apply_file_mutation(request, outcome)

        manifest = outcome.get("change_manifest")
        if isinstance(manifest, Mapping):
            manifest_path = request.workspace_dir / ".metaharness" / "change_manifest.json"
            manifest_path.parent.mkdir(parents=True, exist_ok=True)
            manifest_path.write_text(json.dumps(dict(manifest), indent=2, sort_keys=True), encoding="utf-8")

        stdout_path.write_text("", encoding="utf-8")
        stderr_path.write_text("", encoding="utf-8")
        execution = ProposalExecution(
            command=["fake-backend"],
            cwd=request.workspace_dir,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            returncode=0,
            metadata={"outcome": outcome},
        )
        return execution

    def collect(self, execution: ProposalExecution) -> ProposalResult:
        outcome = execution.metadata.get("outcome", {})
        files = outcome.get("files")
        if isinstance(files, list) and files:
            changed_files = [
                str(file_spec.get("relative_path"))
                for file_spec in files
                if isinstance(file_spec, Mapping) and file_spec.get("relative_path")
            ]
        else:
            changed_files = [str(outcome.get("relative_path", "README.md"))]

        primary_path = changed_files[0] if changed_files else "README.md"
        summary = str(outcome.get("summary", f"Updated {primary_path}."))
        final_text = str(outcome.get("final_text", summary))
        return ProposalResult(
            applied=True,
            summary=summary,
            final_text=final_text,
            changed_files=changed_files,
            events=[
                AgentEvent(
                    ts=None,
                    kind="file_change",
                    text=summary,
                    file_changes=changed_files,
                )
            ],
            raw_stdout_path=execution.stdout_path,
            raw_stderr_path=execution.stderr_path,
            metadata={"command": execution.command, "returncode": execution.returncode},
        )

    @staticmethod
    def _default_mutation(request: ProposalRequest) -> Mapping[str, Any]:
        return {
            "relative_path": "README.md",
            "content": "# Updated by FakeBackend\n",
            "summary": f"Updated candidate {request.candidate_id}.",
        }

    @staticmethod
    def _apply_file_mutation(request: ProposalRequest, file_spec: Mapping[str, Any]) -> None:
        relative_path = str(file_spec.get("relative_path", "README.md"))
        content = str(file_spec.get("content", "fake backend wrote this file\n"))
        mode = str(file_spec.get("mode", "write"))
        target = request.workspace_dir / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        if mode == "append" and target.exists():
            target.write_text(target.read_text(encoding="utf-8") + content, encoding="utf-8")
        else:
            target.write_text(content, encoding="utf-8")
