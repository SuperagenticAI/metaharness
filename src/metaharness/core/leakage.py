from __future__ import annotations

from pathlib import Path
from typing import Sequence


def collect_leakage_tokens(
    *,
    enabled: bool,
    extra: Sequence[str] | None = None,
    task_ids: Sequence[str] | None = None,
) -> list[str]:
    if not enabled:
        return []
    tokens: list[str] = []
    seen: set[str] = set()
    for value in [*(extra or []), *(task_ids or [])]:
        token = str(value).strip()
        if not token or token in seen:
            continue
        seen.add(token)
        tokens.append(token)
    return tokens


def find_leakage_tokens(
    workspace: Path,
    changed_files: Sequence[str],
    tokens: Sequence[str],
) -> list[str]:
    if not tokens:
        return []
    matched: set[str] = set()
    for relative_path in changed_files:
        normalized = str(relative_path).replace("\\", "/").strip().strip("/")
        if not normalized or normalized == ".metaharness" or normalized.startswith(".metaharness/"):
            continue
        path = workspace / normalized
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for token in tokens:
            if token in text:
                matched.add(token)
    return sorted(matched)
