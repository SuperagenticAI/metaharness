from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ...models import AgentEvent
from ..normalized_events import collect_changed_files, last_text_message


def parse_omnigent_events(paths: list[Path]) -> tuple[list[AgentEvent], str, list[str], dict[str, object]]:
    events: list[AgentEvent] = []
    token_usage = {"input_tokens": 0, "cached_input_tokens": 0, "output_tokens": 0}
    tool_call_count = 0
    files_read: dict[str, dict[str, int]] = {}
    files_written: dict[str, dict[str, int]] = {}
    cost_usd = 0.0
    saw_cost = False

    for path in paths:
        for payload in _load_payloads(path):
            event, usage, cost = _parse_payload(payload)
            events.append(event)
            token_usage["input_tokens"] += int(usage.get("input_tokens", 0))
            token_usage["cached_input_tokens"] += int(usage.get("cached_input_tokens", 0))
            token_usage["output_tokens"] += int(usage.get("output_tokens", 0))
            if event.tool_name:
                tool_call_count += 1
            if cost is not None:
                saw_cost = True
                cost_usd += cost
            for changed_path in event.file_changes:
                bucket = files_written.setdefault(changed_path, {"writes": 0})
                bucket["writes"] += 1
            if event.command:
                for token in event.command.split():
                    if "/" in token and not token.startswith("-"):
                        bucket = files_read.setdefault(token, {"reads": 0})
                        bucket["reads"] += 1

    telemetry: dict[str, object] = {
        "token_usage": token_usage,
        "tool_call_count": tool_call_count,
        "files_read": files_read,
        "files_written": files_written,
    }
    if saw_cost:
        telemetry["cost_usd"] = cost_usd
    return events, last_text_message(events), collect_changed_files(events), telemetry


def _load_payloads(path: Path) -> list[dict[str, Any]]:
    if not path.exists() or not path.is_file():
        return []
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return []

    payloads: list[dict[str, Any]] = []
    payloads.extend(_load_jsonl_payloads(text))
    if payloads:
        return payloads
    payloads.extend(_load_sse_payloads(text))
    if payloads:
        return payloads

    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return []
    if isinstance(payload, dict):
        return [payload]
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    return []


def _load_jsonl_payloads(text: str) -> list[dict[str, Any]]:
    payloads: list[dict[str, Any]] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("data:"):
            return []
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            return []
        if isinstance(payload, dict):
            payloads.append(payload)
    return payloads


def _load_sse_payloads(text: str) -> list[dict[str, Any]]:
    payloads: list[dict[str, Any]] = []
    current_data: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            _append_sse_payload(payloads, current_data)
            current_data = []
            continue
        if line.startswith("data:"):
            current_data.append(line.removeprefix("data:").strip())
    _append_sse_payload(payloads, current_data)
    return payloads


def _append_sse_payload(payloads: list[dict[str, Any]], current_data: list[str]) -> None:
    if not current_data:
        return
    data = "\n".join(current_data).strip()
    if not data or data == "[DONE]":
        return
    try:
        payload = json.loads(data)
    except json.JSONDecodeError:
        return
    if isinstance(payload, dict):
        payloads.append(payload)


def _parse_payload(payload: dict[str, Any]) -> tuple[AgentEvent, dict[str, int], float | None]:
    kind = _event_kind(payload)
    text = _extract_text(payload)
    command = _extract_command(payload)
    output = _extract_output(payload)
    tool_name = _extract_tool_name(payload, kind)
    file_changes = _extract_file_changes(payload, tool_name)
    usage = _extract_usage(payload)
    cost = _extract_cost(payload)
    return (
        AgentEvent(
            ts=_as_str(payload.get("timestamp") or payload.get("created_at") or payload.get("time")),
            kind=kind,
            text=text,
            command=command,
            output=output,
            file_changes=file_changes,
            tool_name=tool_name,
            raw=payload,
        ),
        usage,
        cost,
    )


def _event_kind(payload: dict[str, Any]) -> str:
    for key in ("type", "event", "kind"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return "omnigent.event"


def _extract_text(payload: dict[str, Any]) -> str | None:
    for key in ("text", "message", "content", "delta", "summary"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value
    response = payload.get("response")
    if isinstance(response, dict):
        for key in ("text", "message", "content", "output_text"):
            value = response.get(key)
            if isinstance(value, str) and value.strip():
                return value
    item = payload.get("item")
    if isinstance(item, dict):
        return _extract_text(item)
    data = payload.get("data")
    if isinstance(data, dict):
        return _extract_text(data)
    return None


def _extract_command(payload: dict[str, Any]) -> str | None:
    for key in ("command", "cmd", "shell_command"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value
    args = payload.get("args") or payload.get("arguments") or payload.get("parameters")
    if isinstance(args, dict):
        for key in ("command", "cmd", "shell_command"):
            value = args.get(key)
            if isinstance(value, str) and value.strip():
                return value
    item = payload.get("item")
    if isinstance(item, dict):
        return _extract_command(item)
    return None


def _extract_output(payload: dict[str, Any]) -> str | None:
    for key in ("output", "result", "error", "stderr", "stdout"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value
        if isinstance(value, dict):
            message = value.get("message")
            if isinstance(message, str) and message.strip():
                return message
    data = payload.get("data")
    if isinstance(data, dict):
        return _extract_output(data)
    return None


def _extract_tool_name(payload: dict[str, Any], kind: str) -> str | None:
    for key in ("tool_name", "toolName", "tool", "name"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip() and ("tool" in kind or value.startswith("sys_")):
            return value
    item = payload.get("item")
    if isinstance(item, dict):
        nested = _extract_tool_name(item, kind)
        if nested:
            return nested
    data = payload.get("data")
    if isinstance(data, dict):
        nested = _extract_tool_name(data, kind)
        if nested:
            return nested
    if "tool" in kind:
        return kind
    return None


def _extract_file_changes(payload: dict[str, Any], tool_name: str | None) -> list[str]:
    changed: list[str] = []
    for key in ("file_changes", "fileChanges", "changed_files", "changedFiles", "files"):
        _extend_paths(changed, payload.get(key))

    args = payload.get("args") or payload.get("arguments") or payload.get("parameters")
    if isinstance(args, dict) and _tool_likely_mutates_files(tool_name):
        _extend_paths(changed, args)

    item = payload.get("item")
    if isinstance(item, dict):
        _extend_unique(changed, _extract_file_changes(item, tool_name))
    data = payload.get("data")
    if isinstance(data, dict):
        _extend_unique(changed, _extract_file_changes(data, tool_name))
    return changed


def _extend_paths(changed: list[str], value: Any) -> None:
    if isinstance(value, str) and value.strip():
        _extend_unique(changed, [value])
    elif isinstance(value, list):
        for item in value:
            _extend_paths(changed, item)
    elif isinstance(value, dict):
        for key in ("path", "file_path", "target_path", "new_path", "old_path", "destination_path"):
            nested = value.get(key)
            if isinstance(nested, str) and nested.strip():
                _extend_unique(changed, [nested])


def _extend_unique(values: list[str], additions: list[str]) -> None:
    for value in additions:
        if value not in values:
            values.append(value)


def _tool_likely_mutates_files(tool_name: str | None) -> bool:
    if not tool_name:
        return False
    normalized = tool_name.strip().lower()
    return any(token in normalized for token in ("write", "edit", "replace", "delete", "move", "rename", "create"))


def _extract_usage(payload: dict[str, Any]) -> dict[str, int]:
    usage = payload.get("usage") or payload.get("token_usage") or payload.get("tokenUsage")
    if not isinstance(usage, dict):
        response = payload.get("response")
        usage = response.get("usage") if isinstance(response, dict) else None
    if not isinstance(usage, dict):
        return {"input_tokens": 0, "cached_input_tokens": 0, "output_tokens": 0}
    return {
        "input_tokens": _as_int(
            usage.get("input_tokens")
            or usage.get("prompt_tokens")
            or usage.get("inputTokens")
            or usage.get("promptTokens")
        ),
        "cached_input_tokens": _as_int(
            usage.get("cached_input_tokens")
            or usage.get("cache_read_input_tokens")
            or usage.get("cachedInputTokens")
        ),
        "output_tokens": _as_int(
            usage.get("output_tokens")
            or usage.get("completion_tokens")
            or usage.get("outputTokens")
            or usage.get("completionTokens")
        ),
    }


def _extract_cost(payload: dict[str, Any]) -> float | None:
    for key in ("cost_usd", "costUsd", "cost"):
        value = payload.get(key)
        if isinstance(value, int | float):
            return float(value)
    usage = payload.get("usage")
    if isinstance(usage, dict):
        for key in ("cost_usd", "costUsd", "cost"):
            value = usage.get(key)
            if isinstance(value, int | float):
                return float(value)
    return None


def _as_int(value: Any) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return 0


def _as_str(value: Any) -> str | None:
    return value if isinstance(value, str) else None
