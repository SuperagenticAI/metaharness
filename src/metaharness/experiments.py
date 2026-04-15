from __future__ import annotations

import json
import re
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Sequence

from .integrations.coding_tool.config import CodingToolProject, load_coding_tool_project
from .integrations.coding_tool.runtime import resolve_backend_options, run_coding_tool_project
from .reporting import render_tsv, summarize_run

_TRIAL_TSV_COLUMNS = (
    "experiment_id",
    "benchmark_name",
    "project_dir",
    "backend",
    "backend_label",
    "model",
    "budget",
    "trial_index",
    "run_id",
    "run_dir",
    "best_candidate_id",
    "best_candidate_outcome",
    "best_objective",
    "best_test_objective",
    "baseline_objective",
    "improved",
    "search_mode",
    "selection_policy",
    "proposal_batch_size",
    "candidate_count",
    "keep_candidate_count",
    "discard_candidate_count",
    "crash_candidate_count",
    "timeout_candidate_count",
    "scope_violation_candidate_count",
    "duration_seconds",
    "time_to_first_improvement_seconds",
    "proposal_timeout_seconds",
    "use_oss",
    "local_provider",
)

_AGGREGATE_TSV_COLUMNS = (
    "benchmark_name",
    "backend",
    "backend_label",
    "model",
    "budget",
    "trial_count",
    "improved_count",
    "success_rate",
    "mean_best_objective",
    "mean_best_test_objective",
    "max_best_objective",
    "mean_duration_seconds",
    "mean_time_to_first_improvement_seconds",
    "timeout_run_rate",
    "crash_run_rate",
    "scope_violation_run_rate",
    "mean_keep_candidate_count",
)


def default_experiment_dir(project_dir: str | Path) -> Path:
    timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    project_dir = Path(project_dir).resolve()
    return project_dir / "experiments" / f"experiment-{timestamp}"


def run_experiment_matrix(
    project_dirs: Sequence[str | Path],
    *,
    backends: Sequence[str],
    budgets: Sequence[int] | None = None,
    trial_count: int = 1,
    models: Sequence[str] | None = None,
    results_dir: str | Path,
    backend_overrides: dict[str, Any] | None = None,
    project_overrides: dict[str, Any] | None = None,
    config_path: str | Path | None = None,
    config_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    experiment_dir = Path(results_dir).resolve()
    experiment_dir.mkdir(parents=True, exist_ok=True)
    experiment_id = experiment_dir.name
    started_at = datetime.now(UTC).isoformat()
    projects = [load_coding_tool_project(Path(project_dir)) for project_dir in project_dirs]

    trial_rows: list[dict[str, Any]] = []
    run_dirs: list[str] = []
    for project in projects:
        project_budgets = list(budgets or [project.default_budget])
        for backend in backends:
            resolved_options = resolve_backend_options(backend, project, overrides=backend_overrides)
            backend_models = _resolve_models(backend, resolved_options, models)
            for model in backend_models:
                for budget in project_budgets:
                    for trial_index in range(1, trial_count + 1):
                        run_name = _build_run_name(
                            experiment_id=experiment_id,
                            benchmark_name=project.root_dir.name,
                            backend=backend,
                            model=model,
                            budget=budget,
                            trial_index=trial_index,
                        )
                        run_result = run_coding_tool_project(
                            project=project,
                            backend_name=backend,
                            budget=budget,
                            run_name=run_name,
                            backend_overrides=_per_run_overrides(backend_overrides, backend, model),
                            search_mode=_project_override(project_overrides, "search_mode"),
                            proposal_batch_size=_project_override(project_overrides, "proposal_batch_size"),
                            selection_policy=_project_override(project_overrides, "selection_policy"),
                        )
                        run_summary = summarize_run(run_result.run_dir)
                        run_dirs.append(str(run_result.run_dir))
                        trial_rows.append(
                            _trial_row(
                                experiment_id=experiment_id,
                                project=project,
                                backend=backend,
                                budget=budget,
                                trial_index=trial_index,
                                run_summary=run_summary,
                            )
                        )

    aggregate_rows = aggregate_experiment_trials(trial_rows)
    completed_at = datetime.now(UTC).isoformat()
    payload = {
        "experiment_dir": str(experiment_dir),
        "experiment_id": experiment_id,
        "started_at": started_at,
        "completed_at": completed_at,
        "project_dirs": [str(project.root_dir) for project in projects],
        "backends": list(backends),
        "budgets": sorted({int(row["budget"]) for row in trial_rows}),
        "trial_count": trial_count,
        "models": sorted({str(row["model"]) for row in trial_rows if row.get("model")}),
        "config_path": str(Path(config_path).resolve()) if config_path is not None else None,
        "config_payload": dict(config_payload or {}),
        "run_dirs": run_dirs,
        "trials": trial_rows,
        "aggregates": aggregate_rows,
        "paths": {
            "metadata_json": str(experiment_dir / "experiment.json"),
            "trials_json": str(experiment_dir / "trials.json"),
            "aggregates_json": str(experiment_dir / "aggregates.json"),
            "trials_tsv": str(experiment_dir / "trials.tsv"),
            "aggregates_tsv": str(experiment_dir / "aggregates.tsv"),
        },
    }
    _write_json(experiment_dir / "experiment.json", payload)
    _write_json(experiment_dir / "trials.json", trial_rows)
    _write_json(experiment_dir / "aggregates.json", aggregate_rows)
    (experiment_dir / "trials.tsv").write_text(render_tsv(trial_rows, _TRIAL_TSV_COLUMNS), encoding="utf-8")
    (experiment_dir / "aggregates.tsv").write_text(
        render_tsv(aggregate_rows, _AGGREGATE_TSV_COLUMNS),
        encoding="utf-8",
    )
    return payload


def aggregate_experiment_trials(trial_rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str, str, int], list[dict[str, Any]]] = {}
    for row in trial_rows:
        key = (
            str(row.get("benchmark_name", "")),
            str(row.get("backend", "")),
            str(row.get("backend_label", "")),
            str(row.get("model", "")),
            int(row.get("budget", 0)),
        )
        grouped.setdefault(key, []).append(dict(row))

    aggregates: list[dict[str, Any]] = []
    for key in sorted(grouped):
        benchmark_name, backend, backend_label, model, budget = key
        rows = grouped[key]
        trial_count = len(rows)
        improved_count = sum(1 for row in rows if bool(row.get("improved")))
        timeout_runs = sum(1 for row in rows if int(row.get("timeout_candidate_count", 0)) > 0)
        crash_runs = sum(1 for row in rows if int(row.get("crash_candidate_count", 0)) > 0)
        scope_violation_runs = sum(1 for row in rows if int(row.get("scope_violation_candidate_count", 0)) > 0)
        aggregates.append(
            {
                "benchmark_name": benchmark_name,
                "backend": backend,
                "backend_label": backend_label,
                "model": model,
                "budget": budget,
                "trial_count": trial_count,
                "improved_count": improved_count,
                "success_rate": _ratio(improved_count, trial_count),
                "mean_best_objective": _mean(row.get("best_objective") for row in rows),
                "mean_best_test_objective": _mean(row.get("best_test_objective") for row in rows),
                "max_best_objective": _max(row.get("best_objective") for row in rows),
                "mean_duration_seconds": _mean(row.get("duration_seconds") for row in rows),
                "mean_time_to_first_improvement_seconds": _mean(
                    row.get("time_to_first_improvement_seconds") for row in rows
                ),
                "timeout_run_rate": _ratio(timeout_runs, trial_count),
                "crash_run_rate": _ratio(crash_runs, trial_count),
                "scope_violation_run_rate": _ratio(scope_violation_runs, trial_count),
                "mean_keep_candidate_count": _mean(row.get("keep_candidate_count") for row in rows),
            }
        )
    return aggregates


def render_experiment_aggregate_table(rows: Sequence[dict[str, Any]]) -> str:
    if not rows:
        return "No experiment results."

    headers = [
        "benchmark",
        "backend",
        "budget",
        "trials",
        "success_rate",
        "mean_best",
        "timeout_rate",
        "crash_rate",
        "scope_viol",
    ]
    rendered_rows = []
    for row in rows:
        rendered_rows.append(
            [
                str(row.get("benchmark_name", "")),
                str(row.get("backend_label", "")),
                str(row.get("budget", "")),
                str(row.get("trial_count", "")),
                _format_float(row.get("success_rate")),
                _format_float(row.get("mean_best_objective")),
                _format_float(row.get("timeout_run_rate")),
                _format_float(row.get("crash_run_rate")),
                _format_float(row.get("scope_violation_run_rate")),
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


def trial_tsv_columns() -> tuple[str, ...]:
    return _TRIAL_TSV_COLUMNS


def aggregate_tsv_columns() -> tuple[str, ...]:
    return _AGGREGATE_TSV_COLUMNS


def _trial_row(
    *,
    experiment_id: str,
    project: CodingToolProject,
    backend: str,
    budget: int,
    trial_index: int,
    run_summary: dict[str, Any],
) -> dict[str, Any]:
    return {
        "experiment_id": experiment_id,
        "benchmark_name": run_summary.get("benchmark_name"),
        "project_dir": str(project.root_dir),
        "backend": backend,
        "backend_label": run_summary.get("backend_label"),
        "model": run_summary.get("model") or "",
        "budget": budget,
        "trial_index": trial_index,
        "run_id": run_summary.get("run_id"),
        "run_dir": run_summary.get("run_dir"),
        "best_candidate_id": run_summary.get("best_candidate_id"),
        "best_candidate_outcome": run_summary.get("best_candidate_outcome"),
        "best_objective": run_summary.get("best_objective"),
        "best_test_objective": run_summary.get("best_test_objective"),
        "baseline_objective": run_summary.get("baseline_objective"),
        "improved": run_summary.get("improved"),
        "search_mode": run_summary.get("search_mode"),
        "selection_policy": run_summary.get("selection_policy"),
        "proposal_batch_size": run_summary.get("proposal_batch_size"),
        "candidate_count": run_summary.get("candidate_count"),
        "keep_candidate_count": run_summary.get("keep_candidate_count"),
        "discard_candidate_count": run_summary.get("discard_candidate_count"),
        "crash_candidate_count": run_summary.get("crash_candidate_count"),
        "timeout_candidate_count": run_summary.get("timeout_candidate_count"),
        "scope_violation_candidate_count": run_summary.get("scope_violation_candidate_count"),
        "duration_seconds": run_summary.get("duration_seconds"),
        "time_to_first_improvement_seconds": run_summary.get("time_to_first_improvement_seconds"),
        "proposal_timeout_seconds": run_summary.get("proposal_timeout_seconds"),
        "use_oss": run_summary.get("use_oss"),
        "local_provider": run_summary.get("local_provider") or "",
    }


def _resolve_models(
    backend: str,
    resolved_options: dict[str, Any],
    models: Sequence[str] | None,
) -> list[str | None]:
    if models:
        return [str(value) for value in models]
    if backend not in {"codex", "gemini"}:
        return [None]
    model = resolved_options.get("model")
    if model:
        return [str(model)]
    return [None]


def _per_run_overrides(
    backend_overrides: dict[str, Any] | None,
    backend: str,
    model: str | None,
) -> dict[str, Any] | None:
    overrides = dict(backend_overrides or {})
    if backend != "fake" and model is not None:
        overrides["model"] = model
    return overrides or None


def _project_override(project_overrides: dict[str, Any] | None, key: str):
    if not project_overrides:
        return None
    return project_overrides.get(key)


def _build_run_name(
    *,
    experiment_id: str,
    benchmark_name: str,
    backend: str,
    model: str | None,
    budget: int,
    trial_index: int,
) -> str:
    model_token = model or "default"
    return "-".join(
        [
            _slugify(experiment_id),
            _slugify(benchmark_name),
            _slugify(backend),
            _slugify(model_token),
            f"b{budget}",
            f"t{trial_index:02d}",
        ]
    )


def _slugify(value: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9]+", "-", str(value).strip().lower())
    return text.strip("-") or "item"


def _mean(values: Iterable[Any]) -> float | None:
    numeric = [float(value) for value in values if value is not None]
    if not numeric:
        return None
    return sum(numeric) / len(numeric)


def _max(values: Iterable[Any]) -> float | None:
    numeric = [float(value) for value in values if value is not None]
    if not numeric:
        return None
    return max(numeric)


def _ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return numerator / denominator


def _format_float(value: Any) -> str:
    if value is None:
        return "-"
    return f"{float(value):.3f}"


def _write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
