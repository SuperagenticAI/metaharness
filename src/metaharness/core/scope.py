from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

WRITE_SCOPE_CLASSES = (
    "prompt",
    "tool_desc",
    "tool_impl",
    "middleware",
    "skill",
    "subagent",
    "memory",
    "other",
)

WRITE_SCOPE_MODES = ("all", "single-class")

_SKILL_PREFIXES = (
    ".agents/skills",
    ".claude/skills",
    ".cursor/skills",
    ".gemini/skills",
    "skills",
)

_PROMPT_NAMES = {"agents.md", "claude.md", "gemini.md", "cursor.md"}
_MEMORY_NAMES = {"memory.md"}
_MEMORY_PREFIXES = (".agents/memory", ".claude/memory")
_SUBAGENT_PREFIXES = (".claude/agents", "sub_agents", "subagents")
_MIDDLEWARE_PREFIXES = ("scripts", "hooks", ".claude/hooks", ".agents/hooks")
_TOOL_IMPL_PREFIXES = ("tools",)
_TOOL_DESC_NAMES = {"tools.md"}


@dataclass(slots=True)
class WriteScopeEntry:
    path: str
    write_class: str


def normalize_write_class(value: str) -> str:
    text = str(value).strip().lower().replace("-", "_")
    aliases = {
        "prompts": "prompt",
        "instruction": "prompt",
        "instructions": "prompt",
        "skills": "skill",
        "agent_skill": "skill",
        "sub_agent": "subagent",
        "sub-agent": "subagent",
        "tool": "tool_impl",
        "tools": "tool_impl",
        "hook": "middleware",
        "hooks": "middleware",
        "script": "middleware",
        "scripts": "middleware",
    }
    text = aliases.get(text, text)
    if text not in WRITE_SCOPE_CLASSES:
        raise ValueError(f"unsupported write-scope class: {value}")
    return text


def normalize_write_scope_mode(value: str | None) -> str:
    mode = str(value or "all").strip().lower()
    if mode not in WRITE_SCOPE_MODES:
        raise ValueError(f"unsupported write_scope_mode: {value}")
    return mode


def infer_write_class(path: str) -> str:
    normalized = _normalize_relative_path(path) or "."
    lowered = normalized.lower()
    name = lowered.rsplit("/", 1)[-1]
    if name == "skill.md" or any(_path_is_under(lowered, prefix) for prefix in _SKILL_PREFIXES):
        return "skill"
    if name in _PROMPT_NAMES:
        return "prompt"
    if name in _MEMORY_NAMES or any(_path_is_under(lowered, prefix) for prefix in _MEMORY_PREFIXES):
        return "memory"
    if any(_path_is_under(lowered, prefix) for prefix in _SUBAGENT_PREFIXES):
        return "subagent"
    if name in _TOOL_DESC_NAMES:
        return "tool_desc"
    if any(_path_is_under(lowered, prefix) for prefix in _TOOL_IMPL_PREFIXES):
        return "tool_impl"
    if any(_path_is_under(lowered, prefix) for prefix in _MIDDLEWARE_PREFIXES):
        return "middleware"
    return "other"


def parse_allowed_write_paths(raw: Any) -> tuple[list[str], list[WriteScopeEntry]]:
    if raw is None:
        return [], []
    if not isinstance(raw, list):
        raise ValueError("allowed_write_paths must be a list of paths or {path, class} objects")
    paths: list[str] = []
    entries: list[WriteScopeEntry] = []
    for item in raw:
        if isinstance(item, dict):
            path = str(item.get("path", "")).strip()
            if not path:
                raise ValueError("allowed_write_paths object is missing required field 'path'")
            write_class = str(item.get("class") or infer_write_class(path))
        else:
            path = str(item).strip()
            if not path:
                continue
            write_class = infer_write_class(path)
        normalized_path = _normalize_relative_path(path) or "."
        paths.append(normalized_path)
        entries.append(WriteScopeEntry(path=normalized_path, write_class=normalize_write_class(write_class)))
    return paths, entries


def class_for_path(path: str, entries: Sequence[WriteScopeEntry]) -> str:
    normalized = _normalize_relative_path(path)
    if normalized is None:
        return "other"
    matched: WriteScopeEntry | None = None
    matched_len = -1
    for entry in entries:
        if _path_is_under(normalized, entry.path) and len(entry.path) > matched_len:
            matched = entry
            matched_len = len(entry.path)
    if matched is not None:
        return matched.write_class
    return infer_write_class(normalized)


def class_violations(
    changed_files: Sequence[str],
    entries: Sequence[WriteScopeEntry],
    mode: str,
) -> list[str]:
    if normalize_write_scope_mode(mode) != "single-class":
        return []
    classes: set[str] = set()
    for path in changed_files:
        normalized = _normalize_relative_path(path)
        if normalized is None or _is_internal_path(normalized):
            continue
        classes.add(class_for_path(normalized, entries))
    if len(classes) > 1:
        return sorted(classes)
    return []


def _is_internal_path(path: str) -> bool:
    return path == ".metaharness" or path.startswith(".metaharness/")


def _path_is_under(path: str, prefix: str) -> bool:
    if prefix in {"*", "."}:
        return True
    if path == prefix:
        return True
    return path.startswith(f"{prefix}/")


def _normalize_relative_path(value: str) -> str | None:
    text = str(value).replace("\\", "/").strip().strip("/")
    if not text or text in {".", ".."}:
        return None
    parts = [part for part in text.split("/") if part not in {"", "."}]
    if any(part == ".." for part in parts):
        return None
    return "/".join(parts)
