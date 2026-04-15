from __future__ import annotations

import os
import platform
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from shutil import which
from typing import Any, Sequence

_DEFAULT_TOOL_NAMES = (
    "python",
    "python3",
    "uv",
    "pip",
    "git",
    "rg",
    "bash",
    "sh",
    "node",
    "npm",
    "pnpm",
    "yarn",
    "bun",
    "pytest",
    "make",
    "docker",
    "codex",
    "gemini",
    "ollama",
)

_PACKAGE_FILE_NAMES = (
    "pyproject.toml",
    "uv.lock",
    "requirements.txt",
    "package.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "bun.lock",
    "go.mod",
    "Cargo.toml",
    "Gemfile",
    "Makefile",
    "Dockerfile",
)


@dataclass(slots=True)
class EnvironmentBootstrap:
    summary_text: str
    snapshot: dict[str, Any]


def collect_environment_bootstrap(
    workspace_dir: Path,
    *,
    tool_names: Sequence[str] | None = None,
    max_top_level_entries: int = 20,
    max_git_status_lines: int = 20,
) -> EnvironmentBootstrap:
    workspace_dir = workspace_dir.resolve()
    top_level_entries = _collect_top_level_entries(workspace_dir, max_top_level_entries)
    package_files = [name for name in _PACKAGE_FILE_NAMES if (workspace_dir / name).exists()]
    detected_tools = _detect_tools(tool_names or _DEFAULT_TOOL_NAMES)
    git_snapshot = _collect_git_snapshot(workspace_dir, max_git_status_lines)
    system_snapshot = {
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "python_executable": sys.executable,
        "total_memory_gib": _detect_total_memory_gib(),
    }
    snapshot = {
        "working_directory": str(workspace_dir),
        "top_level_entries": top_level_entries,
        "package_files": package_files,
        "detected_tools": detected_tools,
        "git": git_snapshot,
        "system": system_snapshot,
    }
    return EnvironmentBootstrap(
        summary_text=_render_bootstrap_summary(snapshot, max_top_level_entries=max_top_level_entries),
        snapshot=snapshot,
    )


def _collect_top_level_entries(workspace_dir: Path, max_top_level_entries: int) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    for path in sorted(workspace_dir.iterdir(), key=lambda item: item.name.lower())[:max_top_level_entries]:
        if path.name == ".metaharness":
            continue
        kind = "dir" if path.is_dir() else "file"
        entries.append({"name": path.name, "kind": kind})
    return entries


def _detect_tools(tool_names: Sequence[str]) -> dict[str, str]:
    detected: dict[str, str] = {}
    for tool_name in tool_names:
        resolved = which(tool_name)
        if resolved:
            detected[tool_name] = resolved
    return detected


def _collect_git_snapshot(workspace_dir: Path, max_git_status_lines: int) -> dict[str, Any]:
    if which("git") is None:
        return {
            "available": False,
            "repository": False,
            "summary": "git is not available",
            "branch": None,
            "repo_root": None,
            "status_lines": [],
        }

    try:
        top_level = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=workspace_dir,
            text=True,
            capture_output=True,
            timeout=2,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {
            "available": True,
            "repository": False,
            "summary": f"git probe failed: {type(exc).__name__}",
            "branch": None,
            "repo_root": None,
            "status_lines": [],
        }

    if top_level.returncode != 0:
        return {
            "available": True,
            "repository": False,
            "summary": "workspace is not inside a git repository",
            "branch": None,
            "repo_root": None,
            "status_lines": [],
        }

    repo_root = top_level.stdout.strip() or None
    try:
        status = subprocess.run(
            ["git", "status", "--short", "--branch"],
            cwd=workspace_dir,
            text=True,
            capture_output=True,
            timeout=2,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {
            "available": True,
            "repository": True,
            "summary": f"git status failed: {type(exc).__name__}",
            "branch": None,
            "repo_root": repo_root,
            "status_lines": [],
        }

    lines = [line.rstrip() for line in status.stdout.splitlines() if line.strip()]
    branch = lines[0] if lines else None
    status_lines = lines[1 : 1 + max_git_status_lines] if lines else []
    if status.returncode == 0:
        summary = "git repository detected"
    else:
        summary = status.stderr.strip() or "git status returned a non-zero exit code"
    return {
        "available": True,
        "repository": True,
        "summary": summary,
        "branch": branch,
        "repo_root": repo_root,
        "status_lines": status_lines,
    }


def _detect_total_memory_gib() -> float | None:
    page_size_key = "SC_PAGE_SIZE"
    page_count_key = "SC_PHYS_PAGES"
    if not hasattr(os, "sysconf"):
        return None
    if page_size_key not in os.sysconf_names or page_count_key not in os.sysconf_names:
        return None
    try:
        page_size = int(os.sysconf(page_size_key))
        page_count = int(os.sysconf(page_count_key))
    except (TypeError, ValueError, OSError):
        return None
    if page_size <= 0 or page_count <= 0:
        return None
    return round((page_size * page_count) / float(1024**3), 1)


def _render_bootstrap_summary(snapshot: dict[str, Any], *, max_top_level_entries: int) -> str:
    lines = ["# Environment Bootstrap", ""]
    lines.append(f"- Working directory: {snapshot['working_directory']}")

    system = snapshot.get("system", {})
    platform_name = system.get("platform")
    if platform_name:
        lines.append(f"- Platform: {platform_name}")
    python_version = system.get("python_version")
    python_executable = system.get("python_executable")
    if python_version and python_executable:
        lines.append(f"- Python: {python_version} ({python_executable})")
    total_memory_gib = system.get("total_memory_gib")
    if total_memory_gib is not None:
        lines.append(f"- Total memory: {total_memory_gib:.1f} GiB")

    package_files = snapshot.get("package_files", [])
    if package_files:
        lines.append(f"- Package and build files: {', '.join(package_files)}")
    else:
        lines.append("- Package and build files: none detected at the workspace root")

    detected_tools = snapshot.get("detected_tools", {})
    if detected_tools:
        tool_items = [f"{name}={path}" for name, path in sorted(detected_tools.items())]
        lines.append(f"- Detected tools: {', '.join(tool_items)}")
    else:
        lines.append("- Detected tools: none from the default probe set")

    lines.extend(["", "## Top-Level Workspace Entries"])
    top_level_entries = snapshot.get("top_level_entries", [])
    if top_level_entries:
        for entry in top_level_entries:
            lines.append(f"- [{entry['kind']}] {entry['name']}")
        if len(top_level_entries) >= max_top_level_entries:
            lines.append(f"- list truncated at {max_top_level_entries} entries")
    else:
        lines.append("- no visible entries")

    lines.extend(["", "## Git State"])
    git_snapshot = snapshot.get("git", {})
    git_summary = git_snapshot.get("summary")
    if git_summary:
        lines.append(f"- Summary: {git_summary}")
    branch = git_snapshot.get("branch")
    if branch:
        lines.append(f"- Branch: {branch}")
    repo_root = git_snapshot.get("repo_root")
    if repo_root:
        lines.append(f"- Repository root: {repo_root}")
    status_lines = git_snapshot.get("status_lines", [])
    if status_lines:
        lines.append("- Status:")
        lines.extend(f"  {line}" for line in status_lines)

    lines.extend(
        [
            "",
            "Use this snapshot for initial workspace reconnaissance so you do not waste early turns on basic discovery commands.",
        ]
    )
    return "\n".join(lines)
