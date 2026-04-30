from __future__ import annotations

import os
import shutil
import subprocess
from typing import Any
from pathlib import Path

from ...api import optimize_harness
from ...extensions import create_backend_from_factory
from ...models import EvaluationResult, ValidationResult
from ...proposer.codex_exec import CodexExecBackend
from ...proposer.fake import FakeBackend
from ...proposer.gemini_cli import GeminiCliBackend
from .config import CodingToolProject, CodingToolTask


class CodingToolValidator:
    def __init__(self, project: CodingToolProject) -> None:
        self.project = project

    def validate(self, workspace: Path) -> ValidationResult:
        missing = [name for name in self.project.required_files if not (workspace / name).exists()]
        if missing:
            return ValidationResult(ok=False, summary=f"Missing files: {', '.join(missing)}")

        empty = [name for name in self.project.required_files if not (workspace / name).read_text(encoding="utf-8").strip()]
        if empty:
            return ValidationResult(ok=False, summary=f"Empty required files: {', '.join(empty)}")

        return ValidationResult(ok=True, summary="Required coding-tool artifacts are present")


class CodingToolEvaluator:
    def __init__(self, project: CodingToolProject, timeout_seconds: int = 10) -> None:
        self.project = project
        self.timeout_seconds = timeout_seconds

    def evaluate(self, workspace: Path) -> EvaluationResult:
        # Backward-compatible API for callers that still expect one stage.
        return self.evaluate_search(workspace)

    def evaluate_search(self, workspace: Path) -> EvaluationResult:
        return self._evaluate_tasks(workspace, self.project.tasks, label="search")

    def evaluate_test(self, workspace: Path) -> EvaluationResult | None:
        if not self.project.test_tasks:
            return None
        return self._evaluate_tasks(workspace, self.project.test_tasks, label="test")

    def _evaluate_tasks(self, workspace: Path, tasks: list[CodingToolTask], label: str) -> EvaluationResult:
        total_weight = 0.0
        hit_weight = 0.0
        details: list[dict[str, str | int | float]] = []

        for task in tasks:
            total_weight += task.weight
            passed, detail = self._evaluate_task(workspace, task)
            if passed:
                hit_weight += task.weight
            details.append(detail)

        score = hit_weight / total_weight if total_weight else 0.0
        summary = f"[{label}] Weighted score {hit_weight:.2f}/{total_weight:.2f} = {score:.3f}"
        failures = [detail for detail in details if detail.get("status") != "passed"]
        if failures:
            rendered = []
            for failure in failures[:8]:
                rendered.append(f"{failure['id']}: {failure['message']}")
            summary += "\nFailures:\n" + "\n".join(rendered)

        return EvaluationResult(
            objective=score,
            metrics={"score": score, "weight_hit": hit_weight, "weight_total": total_weight},
            summary=summary,
            metadata={"details": details, "stage": label},
        )

    def _evaluate_task(self, workspace: Path, task: CodingToolTask) -> tuple[bool, dict[str, str | int | float]]:
        if task.type == "file_phrase":
            return self._evaluate_file_phrase_task(workspace, task)
        if task.type == "command":
            return self._evaluate_command_task(workspace, task)
        raise ValueError(f"Unknown coding-tool task type: {task.type}")

    def _evaluate_file_phrase_task(
        self,
        workspace: Path,
        task: CodingToolTask,
    ) -> tuple[bool, dict[str, str | int | float]]:
        path = workspace / str(task.path)
        if not path.exists():
            return False, {"id": task.id, "status": "failed", "message": f"{task.path} missing", "weight": task.weight}
        content = path.read_text(encoding="utf-8")
        missing = [phrase for phrase in task.required_phrases if phrase not in content]
        if missing:
            return (
                False,
                {
                    "id": task.id,
                    "status": "failed",
                    "message": f"{task.path} missing phrases: {', '.join(missing)}",
                    "weight": task.weight,
                },
            )
        return True, {"id": task.id, "status": "passed", "message": f"{task.path} satisfied", "weight": task.weight}

    def _evaluate_command_task(
        self,
        workspace: Path,
        task: CodingToolTask,
    ) -> tuple[bool, dict[str, str | int | float]]:
        shell = _resolve_command_shell()
        try:
            completed = subprocess.run(
                [shell, "-lc", str(task.command)],
                cwd=workspace,
                text=True,
                capture_output=True,
                timeout=self.timeout_seconds,
            )
        except subprocess.TimeoutExpired:
            return False, {
                "id": task.id,
                "status": "failed",
                "message": f"command timed out after {self.timeout_seconds}s: {task.command}",
                "weight": task.weight,
            }
        passed = completed.returncode == task.expect_exit_code
        stdout = completed.stdout.strip()
        stderr = completed.stderr.strip()
        if passed:
            message = f"command succeeded: {task.command}"
        else:
            message = (
                f"command failed ({completed.returncode} != {task.expect_exit_code}): {task.command}"
            )
            if stderr:
                message += f" stderr={stderr}"
            elif stdout:
                message += f" stdout={stdout}"
        return passed, {
            "id": task.id,
            "status": "passed" if passed else "failed",
            "message": message,
            "weight": task.weight,
            "returncode": completed.returncode,
        }


def _resolve_command_shell() -> str:
    env_shell = _resolve_executable(os.environ.get("SHELL"))
    if env_shell:
        return env_shell

    for candidate in ("bash", "zsh", "sh"):
        resolved = _resolve_executable(candidate)
        if resolved:
            return resolved

    return "/bin/sh"


def _resolve_executable(candidate: str | None) -> str | None:
    if not candidate:
        return None
    if os.path.isabs(candidate):
        return candidate if os.path.exists(candidate) else None
    return shutil.which(candidate)


def resolve_backend_options(
    name: str,
    project: CodingToolProject,
    overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    resolved: dict[str, Any] = {}
    plugin_config = project.backend_plugins.get(name)
    if plugin_config is not None:
        resolved.update(dict(plugin_config.options))
    resolved.update(dict(project.backend_configs.get(name, {})))
    for key, value in (overrides or {}).items():
        if value is not None:
            resolved[key] = value
    return resolved


def make_backend(
    name: str,
    project: CodingToolProject,
    overrides: dict[str, Any] | None = None,
):
    options = resolve_backend_options(name=name, project=project, overrides=overrides)
    if name == "codex":
        local_provider = _optional_string(options.get("local_provider"))
        use_oss = bool(options.get("use_oss", False) or local_provider)
        return CodexExecBackend(
            codex_binary=_optional_string(options.get("codex_binary")) or "codex",
            model=_optional_string(options.get("model")),
            sandbox_mode=_optional_string(options.get("sandbox_mode")) or "workspace-write",
            approval_policy=_optional_string(options.get("approval_policy")) or "never",
            extra_writable_dirs=[str(value) for value in options.get("extra_writable_dirs", []) or []],
            extra_args=[str(value) for value in options.get("extra_args", []) or []],
            use_oss=use_oss,
            local_provider=local_provider,
            timeout_seconds=_optional_float(options.get("proposal_timeout_seconds")),
        )
    if name == "gemini":
        return GeminiCliBackend(
            gemini_binary=_optional_string(options.get("gemini_binary")) or "gemini",
            model=_optional_string(options.get("model")),
            output_format=_optional_string(options.get("output_format")) or "stream-json",
            sandbox=options.get("sandbox"),
            approval_mode=_optional_string(options.get("approval_mode")),
            extra_args=[str(value) for value in options.get("extra_args", []) or []],
            timeout_seconds=_optional_float(options.get("proposal_timeout_seconds")),
        )
    if name == "fake":
        if project.example_profile == "coding-tool-python-fixture":
            return _coding_tool_python_fixture_fake_backend()
        if project.example_profile == "coding-tool-python-cli":
            return _coding_tool_python_cli_fake_backend()
        if project.example_profile == "coding-tool-scaffold":
            return _coding_tool_scaffold_fake_backend()
        return FakeBackend()
    plugin_config = project.backend_plugins.get(name)
    if plugin_config is not None:
        return create_backend_from_factory(
            plugin_config.factory,
            backend_name=name,
            project=project,
            options=options,
        )
    raise ValueError(f"unknown backend: {name}")


def run_coding_tool_project(
    project: CodingToolProject,
    backend_name: str,
    budget: int | None = None,
    run_name: str | None = None,
    backend_overrides: dict[str, Any] | None = None,
    trace_evidence_path: Path | None = None,
    search_mode: str | None = None,
    proposal_batch_size: int | None = None,
    selection_policy: str | None = None,
):
    run_id = run_name or f"{backend_name}-run"
    return optimize_harness(
        baseline=project.baseline_dir,
        proposer=make_backend(backend_name, project, overrides=backend_overrides),
        evaluator=CodingToolEvaluator(project),
        validator=CodingToolValidator(project),
        run_dir=project.runs_dir / run_id,
        budget=budget if budget is not None else project.default_budget,
        objective=project.objective,
        constraints=project.constraints,
        allowed_write_paths=project.allowed_write_paths,
        trace_evidence_path=trace_evidence_path,
        search_mode=search_mode or project.search_mode,
        proposal_batch_size=proposal_batch_size if proposal_batch_size is not None else project.proposal_batch_size,
        selection_policy=selection_policy or project.selection_policy,
    )


def _coding_tool_scaffold_fake_backend() -> FakeBackend:
    return FakeBackend(
        mutation=lambda request: {
            "summary": f"Improved coding-tool instructions for {request.candidate_id}.",
            "final_text": "Updated AGENTS.md, GEMINI.md, and helper scripts.",
            "files": [
                {
                    "relative_path": "AGENTS.md",
                    "content": (
                        "# Project Instructions\n\n"
                        "- Be concise.\n"
                        "- Read the repository before editing.\n"
                        "- Never use destructive git commands such as `git reset --hard` or `git checkout --`.\n"
                        "- Prefer running tests with `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q` when Python tests exist.\n"
                    ),
                },
                {
                    "relative_path": "GEMINI.md",
                    "content": (
                        "# Project Context\n\n"
                        "- Read AGENTS.md first.\n"
                        "- Inspect validation and evaluation feedback under .metaharness before editing.\n"
                    ),
                },
                {
                    "relative_path": "scripts/bootstrap.sh",
                    "content": (
                        "#!/usr/bin/env bash\n"
                        "set -euo pipefail\n\n"
                        "grep -q '# Project Instructions' AGENTS.md\n"
                        "grep -q 'Read the repository before editing.' AGENTS.md\n"
                        "grep -q 'Never use destructive git commands' AGENTS.md\n"
                        "echo 'bootstrap checks passed'\n"
                    ),
                },
                {
                    "relative_path": "scripts/validate.sh",
                    "content": (
                        "#!/usr/bin/env bash\n"
                        "set -euo pipefail\n\n"
                        "grep -q 'git reset --hard' AGENTS.md\n"
                        "grep -q 'git checkout --' AGENTS.md\n"
                        "grep -q 'Inspect validation and evaluation feedback under .metaharness before editing.' GEMINI.md\n"
                        "echo 'validation checks passed'\n"
                    ),
                },
                {
                    "relative_path": "scripts/test.sh",
                    "content": (
                        "#!/usr/bin/env bash\n"
                        "set -euo pipefail\n\n"
                        "bash scripts/validate.sh\n"
                        "grep -q 'PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q' AGENTS.md\n"
                        "grep -q 'Read AGENTS.md first.' GEMINI.md\n"
                        "echo 'test checks passed'\n"
                    ),
                },
            ],
        }
    )


def _coding_tool_python_fixture_fake_backend() -> FakeBackend:
    return FakeBackend(
        mutation=lambda request: {
            "summary": f"Improved python-fixture benchmark harness for {request.candidate_id}.",
            "final_text": "Updated AGENTS.md, GEMINI.md, and real bootstrap/validate/test scripts.",
            "files": [
                {
                    "relative_path": "AGENTS.md",
                    "content": (
                        "# Project Instructions\n\n"
                        "- Be concise.\n"
                        "- Read the repository before editing.\n"
                        "- Never use destructive git commands such as `git reset --hard` or `git checkout --`.\n"
                        "- Use `PYTHONPATH=fixture_repo/src .venv/bin/python -m unittest discover -s fixture_repo/tests -v` for the fixture test suite.\n"
                    ),
                },
                {
                    "relative_path": "GEMINI.md",
                    "content": (
                        "# Project Context\n\n"
                        "- Read AGENTS.md first.\n"
                        "- Inspect validation and evaluation feedback under .metaharness before editing.\n"
                    ),
                },
                {
                    "relative_path": "scripts/bootstrap.sh",
                    "content": (
                        "#!/usr/bin/env bash\n"
                        "set -euo pipefail\n\n"
                        "python -m venv .venv\n"
                        ".venv/bin/python -c 'import sys; print(sys.version.split()[0])'\n"
                    ),
                },
                {
                    "relative_path": "scripts/validate.sh",
                    "content": (
                        "#!/usr/bin/env bash\n"
                        "set -euo pipefail\n\n"
                        "grep -q 'Never use destructive git commands' AGENTS.md\n"
                        "grep -q 'Read AGENTS.md first.' GEMINI.md\n"
                        "grep -q 'Inspect validation and evaluation feedback under .metaharness before editing.' GEMINI.md\n"
                        "echo 'validation checks passed'\n"
                    ),
                },
                {
                    "relative_path": "scripts/test.sh",
                    "content": (
                        "#!/usr/bin/env bash\n"
                        "set -euo pipefail\n\n"
                        "PYTHONPATH=fixture_repo/src .venv/bin/python -m unittest discover -s fixture_repo/tests -v\n"
                    ),
                },
            ],
        }
    )


def _coding_tool_python_cli_fake_backend() -> FakeBackend:
    return FakeBackend(
        mutation=lambda request: {
            "summary": f"Improved python-cli benchmark harness for {request.candidate_id}.",
            "final_text": "Updated AGENTS.md, GEMINI.md, and real bootstrap/validate/test scripts.",
            "files": [
                {
                    "relative_path": "AGENTS.md",
                    "content": (
                        "# Project Instructions\n\n"
                        "- Be concise.\n"
                        "- Read the repository before editing.\n"
                        "- Never use destructive git commands such as `git reset --hard` or `git checkout --`.\n"
                        "- Avoid editing fixture_repo unless a task explicitly requires it.\n"
                        "- Use `PYTHONPATH=fixture_repo/src .venv/bin/python -m unittest discover -s fixture_repo/tests -v` for the fixture unit tests.\n"
                        "- Use `PYTHONPATH=fixture_repo/src .venv/bin/python -m benchcli.cli status --config fixture_repo/fixture_config.json` for the CLI smoke check.\n"
                    ),
                },
                {
                    "relative_path": "GEMINI.md",
                    "content": (
                        "# Project Context\n\n"
                        "- Read AGENTS.md first.\n"
                        "- Inspect validation and evaluation feedback under .metaharness before editing.\n"
                    ),
                },
                {
                    "relative_path": "scripts/bootstrap.sh",
                    "content": (
                        "#!/usr/bin/env bash\n"
                        "set -euo pipefail\n\n"
                        "python -m venv .venv\n"
                        ".venv/bin/python -c 'import sys; print(sys.version.split()[0])'\n"
                    ),
                },
                {
                    "relative_path": "scripts/validate.sh",
                    "content": (
                        "#!/usr/bin/env bash\n"
                        "set -euo pipefail\n\n"
                        "grep -q 'Never use destructive git commands' AGENTS.md\n"
                        "grep -q 'Avoid editing fixture_repo unless a task explicitly requires it.' AGENTS.md\n"
                        "grep -q 'Read AGENTS.md first.' GEMINI.md\n"
                        "grep -q 'Inspect validation and evaluation feedback under .metaharness before editing.' GEMINI.md\n"
                        "echo 'validation checks passed'\n"
                    ),
                },
                {
                    "relative_path": "scripts/test.sh",
                    "content": (
                        "#!/usr/bin/env bash\n"
                        "set -euo pipefail\n\n"
                        "PYTHONPATH=fixture_repo/src .venv/bin/python -m unittest discover -s fixture_repo/tests -v\n"
                        "PYTHONPATH=fixture_repo/src .venv/bin/python -m benchcli.cli status --config fixture_repo/fixture_config.json | grep -q '^ready:3$'\n"
                    ),
                },
            ],
        }
    )


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)
