from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Sequence

_TRANSIENT_PREFIXES = (
    ".venv/",
    "__pycache__/",
    ".pytest_cache/",
    ".mypy_cache/",
    ".ruff_cache/",
)

_TRANSIENT_SUFFIXES = (
    ".pyc",
    ".pyo",
)

_MAX_REPORTED_CHANGED_FILES = 20
_SUMMARY_TSV_COLUMNS = (
    "run_id",
    "benchmark_name",
    "backend_label",
    "best_candidate_id",
    "best_objective",
    "baseline_objective",
    "best_candidate_outcome",
    "improved",
    "search_mode",
    "selection_policy",
    "proposal_batch_size",
    "candidate_count",
    "keep_candidate_count",
    "discard_candidate_count",
    "crash_candidate_count",
    "timeout_candidate_count",
    "no_change_candidate_count",
    "scope_violation_candidate_count",
    "duration_seconds",
    "first_improving_candidate_id",
    "best_test_objective",
    "proposal_timeout_seconds",
    "model",
    "use_oss",
    "local_provider",
)
_LEDGER_TSV_COLUMNS = (
    "run_id",
    "benchmark_name",
    "candidate_id",
    "parent_candidate_ids",
    "is_best",
    "objective",
    "valid",
    "proposal_applied",
    "outcome",
    "outcome_summary",
    "changed_file_count",
    "frontier_rank",
    "search_objective",
    "test_objective",
    "token_input",
    "token_output",
    "cost_usd",
    "tool_call_count",
    "changed_files",
    "scope_violation_paths",
    "proposal_summary",
    "validation_summary",
    "evaluation_summary",
)


def summarize_run(run_dir: str | Path) -> dict[str, Any]:
    run_dir = Path(run_dir).resolve()
    run_config = _read_json(run_dir / "run_config.json")
    leaderboard = _read_json(run_dir / "indexes" / "leaderboard.json")
    candidates = _load_candidate_manifests(run_dir / "candidates")
    baseline = _find_candidate(candidates, "c0000")
    best = _find_candidate(candidates, str(leaderboard.get("best_candidate_id", "c0000")))
    proposal = _load_first_candidate_proposal(run_dir / "candidates")
    best_proposal = _load_candidate_proposal(run_dir / "candidates", str(leaderboard.get("best_candidate_id", "c0000")))

    baseline_objective = _as_float(baseline.get("search_objective", baseline.get("objective")))
    best_objective = _as_float(leaderboard.get("best_objective"))
    best_test_objective = _as_float(best.get("test_objective")) if isinstance(best, dict) else None
    started_at = run_config.get("started_at")
    completed_at = leaderboard.get("completed_at")
    duration_seconds = _duration_seconds(started_at, completed_at)

    first_improving_candidate = None
    first_improving_candidate_data: dict[str, Any] | None = None
    if baseline_objective is not None:
        for candidate in sorted(candidates, key=lambda item: item["candidate_id"]):
            objective = _as_float(candidate.get("search_objective", candidate.get("objective")))
            if objective is not None and objective > baseline_objective:
                first_improving_candidate = candidate["candidate_id"]
                first_improving_candidate_data = candidate
                break

    backend = _extract_backend_summary(run_config, proposal)
    raw_best_changed_files: list[str] = []
    if isinstance(best_proposal, dict):
        raw_best_changed_files = [str(value) for value in best_proposal.get("changed_files", [])]
    filtered_changed_files = _filter_changed_files(raw_best_changed_files)
    best_changed_files = filtered_changed_files[:_MAX_REPORTED_CHANGED_FILES]
    outcome_counts = _count_candidate_outcomes(candidates)

    return {
        "run_dir": str(run_dir),
        "run_id": run_dir.name,
        "benchmark_name": _benchmark_name_from_run_config(run_config),
        "objective": run_config.get("objective"),
        "proposer": run_config.get("proposer"),
        "backend_label": backend["backend_label"],
        "model": backend["model"],
        "use_oss": backend["use_oss"],
        "local_provider": backend["local_provider"],
        "proposal_timeout_seconds": backend["proposal_timeout_seconds"],
        "baseline_objective": baseline_objective,
        "best_candidate_id": leaderboard.get("best_candidate_id"),
        "best_objective": best_objective,
        "best_candidate_outcome": _candidate_outcome(best),
        "improved": leaderboard.get("best_candidate_id") != "c0000",
        "search_mode": str(run_config.get("search_mode", "hill-climb")),
        "selection_policy": str(run_config.get("selection_policy", "single")),
        "proposal_batch_size": int(run_config.get("proposal_batch_size", 1)),
        "first_improving_candidate_id": first_improving_candidate,
        "time_to_first_improvement_seconds": _time_to_candidate(started_at, first_improving_candidate_data),
        "candidate_count": len(candidates),
        "proposal_applied_count": sum(1 for item in candidates if item.get("proposal_applied")),
        "valid_candidate_count": sum(1 for item in candidates if item.get("valid")),
        "candidate_outcome_counts": outcome_counts,
        "keep_candidate_count": outcome_counts.get("keep", 0),
        "discard_candidate_count": outcome_counts.get("discard", 0),
        "crash_candidate_count": outcome_counts.get("crash", 0),
        "timeout_candidate_count": outcome_counts.get("timeout", 0),
        "no_change_candidate_count": outcome_counts.get("no-change", 0),
        "scope_violation_candidate_count": outcome_counts.get("scope-violation", 0),
        "best_changed_files": best_changed_files,
        "best_changed_file_count": len(filtered_changed_files),
        "best_changed_files_truncated_count": max(0, len(filtered_changed_files) - len(best_changed_files)),
        "best_transient_files_omitted_count": max(0, len(raw_best_changed_files) - len(filtered_changed_files)),
        "duration_seconds": duration_seconds,
        "best_test_objective": best_test_objective,
        "started_at": started_at,
        "completed_at": completed_at,
        "best_summary": _proposal_summary(best_proposal),
        "best_workspace_dir": best.get("workspace_dir") if isinstance(best, dict) else None,
    }


def summarize_project_runs(project_dir: str | Path) -> list[dict[str, Any]]:
    project_dir = Path(project_dir).resolve()
    runs_dir = project_dir / "runs"
    if not runs_dir.exists():
        return []

    summaries = [summarize_run(path) for path in sorted(runs_dir.iterdir()) if path.is_dir()]
    summaries.sort(key=lambda item: (_sort_float(item.get("best_objective")), item["run_id"]), reverse=True)
    return summaries


def compare_runs(run_dirs: Sequence[str | Path]) -> list[dict[str, Any]]:
    return [summarize_run(run_dir) for run_dir in run_dirs]


def candidate_ledger(run_dir: str | Path) -> list[dict[str, Any]]:
    run_dir = Path(run_dir).resolve()
    run_config = _read_json(run_dir / "run_config.json")
    leaderboard = _read_json(run_dir / "indexes" / "leaderboard.json")
    candidates_dir = run_dir / "candidates"
    candidates = _load_candidate_manifests(candidates_dir)
    best_candidate_id = str(leaderboard.get("best_candidate_id", "c0000"))
    benchmark_name = _benchmark_name_from_run_config(run_config)

    rows: list[dict[str, Any]] = []
    for candidate in sorted(candidates, key=lambda item: item.get("candidate_id", "")):
        candidate_id = str(candidate.get("candidate_id"))
        proposal = _load_candidate_proposal(candidates_dir, candidate_id)
        validation = _load_candidate_stage_result(candidates_dir, candidate_id, "validation")
        evaluation = _load_candidate_stage_result(candidates_dir, candidate_id, "evaluation")
        raw_changed_files = [
            str(value) for value in (proposal.get("changed_files", []) if isinstance(proposal, dict) else [])
        ]
        filtered_changed_files = _filter_changed_files(raw_changed_files)
        token_usage = proposal.get("token_usage", {}) if isinstance(proposal, dict) else {}
        rows.append(
            {
                "run_id": run_dir.name,
                "benchmark_name": benchmark_name,
                "candidate_id": candidate_id,
                "parent_candidate_ids": [str(value) for value in candidate.get("parent_candidate_ids", [])],
                "is_best": candidate_id == best_candidate_id,
                "objective": _as_float(candidate.get("objective")),
                "search_objective": _as_float(candidate.get("search_objective", candidate.get("objective"))),
                "test_objective": _as_float(candidate.get("test_objective")),
                "valid": bool(candidate.get("valid")),
                "proposal_applied": bool(candidate.get("proposal_applied")),
                "outcome": _candidate_outcome(candidate),
                "outcome_summary": str(candidate.get("outcome_summary") or ""),
                "changed_file_count": len(filtered_changed_files),
                "frontier_rank": candidate.get("frontier_rank"),
                "token_input": int(token_usage.get("input_tokens", 0)) if isinstance(token_usage, dict) else 0,
                "token_output": int(token_usage.get("output_tokens", 0)) if isinstance(token_usage, dict) else 0,
                "cost_usd": _as_float(proposal.get("cost_usd")) if isinstance(proposal, dict) else None,
                "tool_call_count": int(proposal.get("tool_call_count", 0)) if isinstance(proposal, dict) else 0,
                "changed_files": filtered_changed_files,
                "scope_violation_paths": [str(value) for value in candidate.get("scope_violation_paths", [])],
                "proposal_summary": _proposal_summary(proposal) or "",
                "validation_summary": _stage_summary(validation),
                "evaluation_summary": _stage_summary(evaluation),
            }
        )
    return rows


def render_run_summary(summary: dict[str, Any]) -> str:
    lines = [
        f"run_dir={summary['run_dir']}",
        f"benchmark={summary['benchmark_name']}",
        f"backend={summary['backend_label']}",
        f"best_candidate_id={summary['best_candidate_id']}",
        f"best_objective={summary['best_objective']}",
        f"best_candidate_outcome={summary.get('best_candidate_outcome')}",
        f"baseline_objective={summary['baseline_objective']}",
        f"improved={summary['improved']}",
        f"search_mode={summary.get('search_mode')}",
        f"selection_policy={summary.get('selection_policy')}",
        f"proposal_batch_size={summary.get('proposal_batch_size')}",
        f"candidate_count={summary['candidate_count']}",
    ]
    if summary.get("candidate_outcome_counts"):
        lines.append(f"candidate_outcomes={_format_outcome_counts(summary['candidate_outcome_counts'])}")
    if summary.get("duration_seconds") is not None:
        lines.append(f"duration_seconds={summary['duration_seconds']:.3f}")
    if summary.get("best_test_objective") is not None:
        lines.append(f"best_test_objective={summary['best_test_objective']:.3f}")
    if summary.get("best_changed_files"):
        lines.append(f"best_changed_files={','.join(summary['best_changed_files'])}")
    if summary.get("best_changed_files_truncated_count"):
        lines.append(f"best_changed_files_truncated={summary['best_changed_files_truncated_count']}")
    if summary.get("best_transient_files_omitted_count"):
        lines.append(f"best_transient_files_omitted={summary['best_transient_files_omitted_count']}")
    if summary.get("best_summary"):
        lines.append(f"best_summary={summary['best_summary']}")
    return "\n".join(lines)


def render_comparison_table(summaries: Sequence[dict[str, Any]]) -> str:
    if not summaries:
        return "No runs found."

    headers = [
        "run_id",
        "benchmark",
        "backend",
        "best_objective",
        "improved",
        "keeps",
        "discards",
        "crashes",
        "timeouts",
        "scope_viol",
        "duration_s",
    ]
    rows = []
    for summary in summaries:
        rows.append(
            [
                str(summary["run_id"]),
                str(summary["benchmark_name"]),
                str(summary["backend_label"]),
                _format_float(summary.get("best_objective")),
                "yes" if summary.get("improved") else "no",
                str(summary.get("keep_candidate_count", 0)),
                str(summary.get("discard_candidate_count", 0)),
                str(summary.get("crash_candidate_count", 0)),
                str(summary.get("timeout_candidate_count", 0)),
                str(summary.get("scope_violation_candidate_count", 0)),
                _format_float(summary.get("duration_seconds")),
            ]
        )

    widths = [len(header) for header in headers]
    for row in rows:
        for index, value in enumerate(row):
            widths[index] = max(widths[index], len(value))

    rendered = [
        "  ".join(header.ljust(widths[index]) for index, header in enumerate(headers)),
        "  ".join("-" * widths[index] for index in range(len(headers))),
    ]
    for row in rows:
        rendered.append("  ".join(value.ljust(widths[index]) for index, value in enumerate(row)))
    return "\n".join(rendered)


def render_candidate_ledger_table(rows: Sequence[dict[str, Any]]) -> str:
    if not rows:
        return "No candidates found."

    headers = [
        "candidate_id",
        "outcome",
        "objective",
        "valid",
        "applied",
        "changed_files",
        "is_best",
    ]
    rendered_rows = []
    for row in rows:
        rendered_rows.append(
            [
                str(row.get("candidate_id", "")),
                str(row.get("outcome", "")),
                _format_float(row.get("objective")),
                "yes" if row.get("valid") else "no",
                "yes" if row.get("proposal_applied") else "no",
                str(row.get("changed_file_count", 0)),
                "yes" if row.get("is_best") else "no",
            ]
        )

    widths = [len(header) for header in headers]
    for row in rendered_rows:
        for index, value in enumerate(row):
            widths[index] = max(widths[index], len(value))

    lines = [
        "  ".join(header.ljust(widths[index]) for index, header in enumerate(headers)),
        "  ".join("-" * widths[index] for index in range(len(headers))),
    ]
    for row in rendered_rows:
        lines.append("  ".join(value.ljust(widths[index]) for index, value in enumerate(row)))
    return "\n".join(lines)


def render_tsv(rows: Sequence[dict[str, Any]], columns: Sequence[str]) -> str:
    lines = ["\t".join(columns)]
    for row in rows:
        lines.append("\t".join(_tsv_cell(row.get(column)) for column in columns))
    return "\n".join(lines)


def summary_tsv_columns() -> tuple[str, ...]:
    return _SUMMARY_TSV_COLUMNS


def ledger_tsv_columns() -> tuple[str, ...]:
    return _LEDGER_TSV_COLUMNS


def _extract_backend_summary(run_config: dict[str, Any], proposal: dict[str, Any] | None) -> dict[str, Any]:
    proposer = str(run_config.get("proposer", "unknown"))
    metadata = proposal.get("metadata", {}) if isinstance(proposal, dict) else {}
    model = None
    if isinstance(metadata, dict):
        command = metadata.get("command", [])
        if isinstance(command, list):
            model = _extract_command_flag(command, "-m")

    use_oss = bool(metadata.get("use_oss")) if isinstance(metadata, dict) else False
    local_provider = metadata.get("local_provider") if isinstance(metadata, dict) else None
    timeout_seconds = metadata.get("timeout_seconds") if isinstance(metadata, dict) else None

    backend_label = proposer
    if use_oss and local_provider:
        backend_label = f"{proposer}:{local_provider}:{model or 'default'}"
    elif model:
        backend_label = f"{proposer}:{model}"

    return {
        "backend_label": backend_label,
        "model": model,
        "use_oss": use_oss,
        "local_provider": local_provider,
        "proposal_timeout_seconds": timeout_seconds,
    }


def _benchmark_name_from_run_config(run_config: dict[str, Any]) -> str:
    baseline = run_config.get("baseline")
    if not baseline:
        return "unknown"
    return Path(str(baseline)).resolve().parent.name


def _proposal_summary(proposal: dict[str, Any] | None) -> str | None:
    if not isinstance(proposal, dict):
        return None
    summary = proposal.get("summary")
    return str(summary) if summary is not None else None


def _stage_summary(result: dict[str, Any] | None) -> str:
    if not isinstance(result, dict):
        return ""
    summary = result.get("summary")
    return str(summary) if summary is not None else ""


def _load_candidate_manifests(candidates_dir: Path) -> list[dict[str, Any]]:
    manifests = []
    if not candidates_dir.exists():
        return manifests
    for candidate_dir in sorted(path for path in candidates_dir.iterdir() if path.is_dir()):
        manifest_path = candidate_dir / "manifest.json"
        if manifest_path.exists():
            manifests.append(_read_json(manifest_path))
    return manifests


def _load_first_candidate_proposal(candidates_dir: Path) -> dict[str, Any] | None:
    if not candidates_dir.exists():
        return None
    for candidate_dir in sorted(path for path in candidates_dir.iterdir() if path.is_dir() and path.name != "c0000"):
        proposal = _load_candidate_proposal(candidates_dir, candidate_dir.name)
        if proposal is not None:
            return proposal
    return None


def _load_candidate_proposal(candidates_dir: Path, candidate_id: str) -> dict[str, Any] | None:
    proposal_path = candidates_dir / candidate_id / "proposal" / "result.json"
    if not proposal_path.exists():
        return None
    return _read_json(proposal_path)


def _load_candidate_stage_result(candidates_dir: Path, candidate_id: str, stage: str) -> dict[str, Any] | None:
    path = candidates_dir / candidate_id / stage / "result.json"
    if stage == "evaluation":
        search_path = candidates_dir / candidate_id / stage / "search_result.json"
        if search_path.exists():
            path = search_path
    if not path.exists():
        return None
    return _read_json(path)


def _find_candidate(candidates: list[dict[str, Any]], candidate_id: str) -> dict[str, Any]:
    for candidate in candidates:
        if candidate.get("candidate_id") == candidate_id:
            return candidate
    return {}


def _candidate_outcome(candidate: dict[str, Any]) -> str:
    outcome = candidate.get("outcome")
    if outcome:
        return str(outcome)
    if candidate.get("candidate_id") == "c0000":
        return "baseline"
    return "unknown"


def _count_candidate_outcomes(candidates: Sequence[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for candidate in candidates:
        outcome = _candidate_outcome(candidate)
        counts[outcome] = counts.get(outcome, 0) + 1
    return counts


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _duration_seconds(started_at: Any, completed_at: Any) -> float | None:
    if not started_at or not completed_at:
        return None
    try:
        started = datetime.fromisoformat(str(started_at))
        completed = datetime.fromisoformat(str(completed_at))
    except ValueError:
        return None
    return max(0.0, (completed - started).total_seconds())


def _time_to_candidate(started_at: Any, candidate: dict[str, Any] | None) -> float | None:
    if not started_at or not isinstance(candidate, dict):
        return None
    updated_at = candidate.get("updated_at")
    if not updated_at:
        return None
    return _duration_seconds(started_at, updated_at)


def _extract_command_flag(command: list[Any], flag: str) -> str | None:
    for index, value in enumerate(command):
        if value == flag and index + 1 < len(command):
            return str(command[index + 1])
    return None


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _sort_float(value: Any) -> float:
    parsed = _as_float(value)
    return parsed if parsed is not None else float("-inf")


def _format_float(value: Any) -> str:
    parsed = _as_float(value)
    if parsed is None:
        return "-"
    return f"{parsed:.3f}"


def _format_outcome_counts(counts: dict[str, int]) -> str:
    items = [f"{key}:{counts[key]}" for key in sorted(counts)]
    return ",".join(items)


def _tsv_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return f"{value:.6f}"
    if isinstance(value, list):
        return ",".join(_tsv_cell(item) for item in value)
    if isinstance(value, dict):
        normalized = {str(key): int(count) for key, count in value.items()}
        return _format_outcome_counts(normalized)
    return str(value).replace("\t", " ").replace("\n", " ")


def _filter_changed_files(paths: Sequence[str]) -> list[str]:
    filtered: list[str] = []
    for path in paths:
        if path.startswith(_TRANSIENT_PREFIXES):
            continue
        if path.endswith(_TRANSIENT_SUFFIXES):
            continue
        filtered.append(path)
    return filtered
