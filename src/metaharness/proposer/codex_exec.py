from __future__ import annotations

import json
import re
import subprocess
from shutil import which
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen

from ..models import ProposalExecution, ProposalRequest, ProposalResult
from .base import ProposerBackend
from .parsers.codex import parse_codex_jsonl


class CodexExecBackend(ProposerBackend):
    name = "codex"

    def __init__(
        self,
        codex_binary: str = "codex",
        model: str | None = None,
        sandbox_mode: str = "workspace-write",
        approval_policy: str = "never",
        extra_writable_dirs: list[str] | None = None,
        extra_args: list[str] | None = None,
        use_oss: bool = False,
        local_provider: str | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        self.codex_binary = codex_binary
        self.model = model
        self.sandbox_mode = sandbox_mode
        self.approval_policy = approval_policy
        self.extra_writable_dirs = extra_writable_dirs or []
        self.extra_args = extra_args or []
        self.use_oss = use_oss
        self.local_provider = local_provider
        self.timeout_seconds = timeout_seconds

    def prepare(self, request: ProposalRequest) -> ProposalRequest:
        return request

    def invoke(self, request: ProposalRequest) -> ProposalExecution:
        proposal_dir = request.candidate_dir / "proposal"
        proposal_dir.mkdir(parents=True, exist_ok=True)
        stdout_path = proposal_dir / "stdout.jsonl"
        stderr_path = proposal_dir / "stderr.txt"
        last_message_path = proposal_dir / "last_message.txt"

        command = [self.codex_binary, "-a", self.approval_policy, "exec"]
        if self.model:
            command.extend(["-m", self.model])
        if self.use_oss:
            command.append("--oss")
        if self.local_provider:
            command.extend(["--local-provider", self.local_provider])
        command.extend(
            [
                "--json",
                "--skip-git-repo-check",
                "-C",
                str(request.workspace_dir),
                "-s",
                self.sandbox_mode,
                "-o",
                str(last_message_path),
                "-",
            ]
        )
        for extra_dir in self.extra_writable_dirs:
            command.extend(["--add-dir", extra_dir])
        command.extend(self.extra_args)

        prompt = request.prompt_path.read_text(encoding="utf-8")
        timed_out = False
        timeout_message = ""
        try:
            completed = subprocess.run(
                command,
                input=prompt,
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
                f"Codex proposal timed out after {self.timeout_seconds:g}s."
                if self.timeout_seconds is not None
                else "Codex proposal timed out."
            )
            if timeout_message not in stderr:
                stderr = f"{stderr}\n{timeout_message}".strip()
            returncode = 124

        stdout_path.write_text(stdout, encoding="utf-8")
        stderr_path.write_text(stderr, encoding="utf-8")

        return ProposalExecution(
            command=command,
            cwd=request.workspace_dir,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            last_message_path=last_message_path,
            returncode=returncode,
            metadata={"timed_out": timed_out, "timeout_message": timeout_message},
        )

    def collect(self, execution: ProposalExecution) -> ProposalResult:
        events, parsed_final_text, changed_files, telemetry = parse_codex_jsonl(execution.stdout_path)
        final_text = parsed_final_text
        if execution.last_message_path and execution.last_message_path.exists():
            persisted = execution.last_message_path.read_text(encoding="utf-8").strip()
            if persisted:
                final_text = persisted

        timed_out = bool(execution.metadata.get("timed_out"))
        applied = execution.returncode == 0 and not timed_out
        summary = "Codex execution completed."
        if timed_out:
            summary = str(execution.metadata.get("timeout_message") or "Codex execution timed out.")
        elif not applied:
            summary = "Codex execution failed."
        return ProposalResult(
            applied=applied,
            summary=summary,
            final_text=final_text,
            changed_files=changed_files,
            events=events,
            raw_stdout_path=execution.stdout_path,
            raw_stderr_path=execution.stderr_path,
            token_usage=dict(telemetry.get("token_usage", {})),
            files_read=dict(telemetry.get("files_read", {})),
            files_written=dict(telemetry.get("files_written", {})),
            tool_call_count=int(telemetry.get("tool_call_count", 0)),
            metadata={
                "command": execution.command,
                "returncode": execution.returncode,
                "use_oss": self.use_oss,
                "local_provider": self.local_provider,
                "timeout_seconds": self.timeout_seconds,
                "timed_out": timed_out,
            },
        )


def probe_codex_cli(codex_binary: str = "codex", timeout_seconds: int = 5) -> dict[str, Any]:
    resolved_binary = which(codex_binary)
    if resolved_binary is None:
        return {
            "ok": False,
            "binary": codex_binary,
            "resolved_binary": None,
            "version": None,
            "returncode": None,
            "raw_output": "",
            "error": f"Could not find binary: {codex_binary}",
        }

    try:
        completed = subprocess.run(
            [codex_binary, "--version"],
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "binary": codex_binary,
            "resolved_binary": resolved_binary,
            "version": None,
            "returncode": None,
            "raw_output": "",
            "error": f"Timed out after {timeout_seconds}s probing {codex_binary}",
        }

    raw_output = "\n".join(
        value for value in [completed.stdout.strip(), completed.stderr.strip()] if value
    ).strip()
    version = _extract_codex_version(raw_output)
    return {
        "ok": completed.returncode == 0,
        "binary": codex_binary,
        "resolved_binary": resolved_binary,
        "version": version,
        "returncode": completed.returncode,
        "raw_output": raw_output,
        "error": None if completed.returncode == 0 else raw_output or "codex --version failed",
    }


def probe_ollama_server(
    base_url: str = "http://127.0.0.1:11434",
    timeout_seconds: int = 2,
) -> dict[str, Any]:
    version_url = f"{base_url.rstrip('/')}/api/version"
    tags_url = f"{base_url.rstrip('/')}/api/tags"
    try:
        version_payload = _fetch_json(version_url, timeout_seconds)
        tags_payload = _fetch_json(tags_url, timeout_seconds)
    except Exception as exc:
        return {
            "ok": False,
            "base_url": base_url,
            "version": None,
            "models": [],
            "error": f"{type(exc).__name__}: {exc}",
        }

    models = []
    for item in tags_payload.get("models", []) or []:
        if not isinstance(item, dict):
            continue
        model_name = item.get("model") or item.get("name")
        if model_name:
            models.append(str(model_name))
    return {
        "ok": True,
        "base_url": base_url,
        "version": version_payload.get("version"),
        "models": models,
        "error": None,
    }


def _extract_codex_version(text: str) -> str | None:
    match = re.search(r"\bcodex-cli\s+([^\s]+)", text)
    if match:
        return match.group(1)
    return None


def _fetch_json(url: str, timeout_seconds: int) -> dict[str, Any]:
    with urlopen(url, timeout=timeout_seconds) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        payload = response.read().decode(charset)
    data = json.loads(payload)
    if not isinstance(data, dict):
        raise URLError(f"unexpected JSON payload from {url}")
    return data


def _coerce_timeout_stream(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value
