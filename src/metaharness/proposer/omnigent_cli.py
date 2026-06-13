from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from shutil import which
from typing import Any

from ..models import AgentEvent, ProposalExecution, ProposalRequest, ProposalResult
from .base import ProposerBackend
from .normalized_events import collect_changed_files, last_text_message
from .parsers.omnigent import parse_omnigent_events


class OmnigentCliBackend(ProposerBackend):
    name = "omnigent"

    def __init__(
        self,
        omnigent_binary: str = "omni",
        harness: str | None = None,
        model: str | None = None,
        agent_config: str | None = None,
        no_session: bool = True,
        sandbox_type: str | None = None,
        allow_network: bool = True,
        event_log_path: str | None = None,
        extra_args: list[str] | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        self.omnigent_binary = omnigent_binary
        self.harness = harness
        self.model = model
        self.agent_config = agent_config
        self.no_session = no_session
        self.sandbox_type = sandbox_type
        self.allow_network = allow_network
        self.event_log_path = event_log_path
        self.extra_args = extra_args or []
        self.timeout_seconds = timeout_seconds

    def prepare(self, request: ProposalRequest) -> ProposalRequest:
        return request

    def invoke(self, request: ProposalRequest) -> ProposalExecution:
        proposal_dir = request.candidate_dir / "proposal"
        proposal_dir.mkdir(parents=True, exist_ok=True)
        stdout_path = proposal_dir / "stdout.txt"
        stderr_path = proposal_dir / "stderr.txt"
        last_message_path = proposal_dir / "last_message.txt"
        artifact_agent_config_path = proposal_dir / "omnigent_agent.yaml"
        generated_agent_dir = request.workspace_dir / ".metaharness" / "omnigent_agent"
        generated_agent_config_path = generated_agent_dir / "config.yaml"
        prompt = _build_user_prompt(request)

        command = self._build_command(agent_config_path=str(generated_agent_dir), prompt=prompt)
        if self.agent_config is None:
            generated_agent_dir.mkdir(parents=True, exist_ok=True)
            generated_agent_config_path.write_text(
                _render_agent_config(
                    harness=self.harness,
                    model=self.model,
                    instructions_path=".metaharness/AGENTS.md",
                    workspace_dir=request.workspace_dir,
                    allowed_write_paths=request.allowed_write_paths,
                    sandbox_type=self.sandbox_type,
                    allow_network=self.allow_network,
                ),
                encoding="utf-8",
            )
            shutil.copyfile(generated_agent_config_path, artifact_agent_config_path)

        timed_out = False
        timeout_message = ""
        try:
            completed = subprocess.run(
                command,
                text=True,
                cwd=request.workspace_dir,
                capture_output=True,
                timeout=self.timeout_seconds,
            )
            stdout = completed.stdout
            stderr = completed.stderr
            returncode = completed.returncode
        except subprocess.TimeoutExpired as exc:
            timed_out = True
            stdout = _coerce_timeout_stream(exc.stdout)
            stderr = _coerce_timeout_stream(exc.stderr)
            timeout_message = (
                f"Omnigent proposal timed out after {self.timeout_seconds:g}s."
                if self.timeout_seconds is not None
                else "Omnigent proposal timed out."
            )
            if timeout_message not in stderr:
                stderr = f"{stderr}\n{timeout_message}".strip()
            returncode = 124
        cleaned_scratch_paths = _cleanup_runtime_scratch(request.workspace_dir)

        stdout_path.write_text(stdout, encoding="utf-8")
        stderr_path.write_text(stderr, encoding="utf-8")
        last_message_path.write_text(stdout.strip(), encoding="utf-8")
        event_log_artifact_path = self._copy_event_log_artifact(
            workspace_dir=request.workspace_dir,
            proposal_dir=proposal_dir,
        )

        return ProposalExecution(
            command=command,
            cwd=request.workspace_dir,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            last_message_path=last_message_path,
            returncode=returncode,
            metadata={
                "timed_out": timed_out,
                "timeout_message": timeout_message,
                "agent_config_path": str(generated_agent_config_path),
                "agent_config_run_path": str(generated_agent_dir),
                "artifact_agent_config_path": str(artifact_agent_config_path),
                "event_log_path": str(event_log_artifact_path) if event_log_artifact_path else None,
                "cleaned_scratch_paths": cleaned_scratch_paths,
            },
        )

    def collect(self, execution: ProposalExecution) -> ProposalResult:
        stdout = execution.stdout_path.read_text(encoding="utf-8") if execution.stdout_path.exists() else ""
        stderr = execution.stderr_path.read_text(encoding="utf-8") if execution.stderr_path.exists() else ""
        event_paths = [execution.stdout_path]
        event_log_path = execution.metadata.get("event_log_path")
        if isinstance(event_log_path, str) and event_log_path:
            event_paths.append(Path(event_log_path))
        parsed_events, parsed_final_text, changed_files, telemetry = parse_omnigent_events(event_paths)
        timed_out = bool(execution.metadata.get("timed_out"))
        applied = execution.returncode == 0 and not timed_out
        summary = "Omnigent execution completed."
        if timed_out:
            summary = str(execution.metadata.get("timeout_message") or "Omnigent execution timed out.")
        elif not applied:
            summary = "Omnigent execution failed."

        events = list(parsed_events)
        if not events and stdout.strip():
            events.append(
                AgentEvent(
                    ts=None,
                    kind="message",
                    text=stdout.strip(),
                    raw={"stream": "stdout"},
                )
            )
        if stderr.strip():
            events.append(
                AgentEvent(
                    ts=None,
                    kind="error",
                    text=stderr.strip(),
                    raw={"stream": "stderr"},
                )
            )

        return ProposalResult(
            applied=applied,
            summary=summary,
            final_text=parsed_final_text or stdout.strip() or last_text_message(events),
            changed_files=changed_files or collect_changed_files(events),
            events=events,
            raw_stdout_path=execution.stdout_path,
            raw_stderr_path=execution.stderr_path,
            token_usage=dict(telemetry.get("token_usage", {})),
            cost_usd=telemetry.get("cost_usd") if isinstance(telemetry.get("cost_usd"), float) else None,
            files_read=dict(telemetry.get("files_read", {})),
            files_written=dict(telemetry.get("files_written", {})),
            tool_call_count=int(telemetry.get("tool_call_count", 0)),
            metadata={
                "command": execution.command,
                "returncode": execution.returncode,
                "omnigent_binary": self.omnigent_binary,
                "harness": self.harness,
                "model": self.model,
                "agent_config": self.agent_config,
                "no_session": self.no_session,
                "sandbox_type": self.sandbox_type,
                "allow_network": self.allow_network,
                "event_log_path": self.event_log_path,
                "event_log_artifact_path": execution.metadata.get("event_log_path"),
                "generated_agent_config_path": execution.metadata.get("agent_config_path"),
                "generated_agent_config_run_path": execution.metadata.get("agent_config_run_path"),
                "artifact_agent_config_path": execution.metadata.get("artifact_agent_config_path"),
                "timeout_seconds": self.timeout_seconds,
                "timed_out": timed_out,
                "cleaned_scratch_paths": execution.metadata.get("cleaned_scratch_paths", []),
            },
        )

    def _build_command(self, *, agent_config_path: str, prompt: str) -> list[str]:
        config_path = self.agent_config or agent_config_path
        command = [self.omnigent_binary, "run", config_path]
        if self.harness:
            command.extend(["--harness", self.harness])
        if self.model:
            command.extend(["--model", self.model])
        if self.no_session:
            command.append("--no-session")
        command.extend(["-p", prompt])
        command.extend(self.extra_args)
        return command

    def _copy_event_log_artifact(self, *, workspace_dir: Path, proposal_dir: Path) -> Path | None:
        if not self.event_log_path:
            return None
        source = Path(self.event_log_path)
        if not source.is_absolute():
            source = workspace_dir / source
        if not source.exists() or not source.is_file():
            return None
        target = proposal_dir / "omnigent_events.jsonl"
        shutil.copyfile(source, target)
        return target


def probe_omnigent_cli(omnigent_binary: str = "omni", timeout_seconds: int = 5) -> dict[str, Any]:
    resolved_binary = which(omnigent_binary)
    if resolved_binary is None:
        return {
            "ok": False,
            "binary": omnigent_binary,
            "resolved_binary": None,
            "version": None,
            "returncode": None,
            "raw_output": "",
            "error": f"Could not find binary: {omnigent_binary}",
        }

    try:
        completed = subprocess.run(
            [omnigent_binary, "--version"],
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "binary": omnigent_binary,
            "resolved_binary": resolved_binary,
            "version": None,
            "returncode": None,
            "raw_output": "",
            "error": f"Timed out after {timeout_seconds}s probing {omnigent_binary}",
        }

    raw_output = "\n".join(
        value for value in [completed.stdout.strip(), completed.stderr.strip()] if value
    ).strip()
    return {
        "ok": completed.returncode == 0,
        "binary": omnigent_binary,
        "resolved_binary": resolved_binary,
        "version": raw_output.split()[-1] if raw_output else None,
        "returncode": completed.returncode,
        "raw_output": raw_output,
        "error": None if completed.returncode == 0 else raw_output or "omni --version failed",
    }


def _build_user_prompt(request: ProposalRequest) -> str:
    parts = [
        "Improve this candidate workspace according to the metaharness instructions.",
        "Read .metaharness/AGENTS.md before editing.",
        "Use .metaharness/bootstrap/summary.md and .metaharness/bootstrap/snapshot.json for workspace context.",
    ]
    if request.trace_evidence_path is not None:
        parts.append("Use .metaharness/evidence/trace_evidence.md as additional trace evidence.")
    parts.append("External validation and evaluation decide whether the candidate is kept.")
    return "\n".join(parts)


def _render_agent_config(
    *,
    harness: str | None,
    model: str | None,
    instructions_path: str,
    workspace_dir: Path,
    allowed_write_paths: list[str],
    sandbox_type: str | None,
    allow_network: bool,
) -> str:
    resolved_sandbox_type = _resolve_sandbox_type(
        configured=sandbox_type,
        allowed_write_paths=allowed_write_paths,
    )
    sandbox: dict[str, Any] = {"type": resolved_sandbox_type}
    if resolved_sandbox_type != "none":
        sandbox["allow_network"] = allow_network
    if allowed_write_paths:
        sandbox["write_paths"] = list(allowed_write_paths)

    payload: dict[str, Any] = {
        "spec_version": 1,
        "name": "metaharness_candidate_proposer",
        "description": "Generated by metaharness for one candidate proposal.",
        "instructions": instructions_path,
        "executor": {
            "type": "omnigent",
            "config": {"harness": harness or "codex"},
        },
        "async": True,
        "cancellable": True,
        "os_env": {
            "type": "caller_process",
            "cwd": str(workspace_dir),
            "sandbox": sandbox,
        },
    }
    if model:
        payload["executor"]["model"] = model
    if allowed_write_paths:
        payload["policies"] = {
            "metaharness_enforce_sandbox": {
                "type": "function",
                "handler": "omnigent.policies.builtins.safety.enforce_sandbox",
                "factory_params": {
                    "sandbox_type": resolved_sandbox_type,
                    "allow_network": allow_network,
                    "write_paths": list(allowed_write_paths),
                },
            }
        }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _resolve_sandbox_type(*, configured: str | None, allowed_write_paths: list[str]) -> str:
    if configured:
        return configured
    if not allowed_write_paths:
        return "none"
    if sys.platform == "darwin":
        return "darwin_seatbelt"
    return "linux_bwrap"


def _coerce_timeout_stream(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def _cleanup_runtime_scratch(workspace_dir: Path) -> list[str]:
    cleaned: list[str] = []
    for relative_path in [".codex-tmp"]:
        path = workspace_dir / relative_path
        if path.exists() and path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
            cleaned.append(relative_path)
    return cleaned
