from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class ExperimentSpec:
    config_path: Path
    config_dir: Path
    project_dirs: list[Path]
    backends: list[str]
    budgets: list[int] = field(default_factory=list)
    trial_count: int = 1
    models: list[str] = field(default_factory=list)
    results_dir: Path | None = None
    backend_overrides: dict[str, Any] = field(default_factory=dict)
    project_overrides: dict[str, Any] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)


def load_experiment_spec(config_path: str | Path) -> ExperimentSpec:
    path = Path(config_path).resolve()
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("experiment config must be a JSON object")

    raw_project_dirs = payload.get("project_dirs", [])
    if not isinstance(raw_project_dirs, list) or not raw_project_dirs:
        raise ValueError("experiment config field 'project_dirs' must be a non-empty array")
    raw_backends = payload.get("backends", [])
    if not isinstance(raw_backends, list) or not raw_backends:
        raise ValueError("experiment config field 'backends' must be a non-empty array")

    raw_budgets = payload.get("budgets", [])
    if raw_budgets is None:
        raw_budgets = []
    if not isinstance(raw_budgets, list):
        raise ValueError("experiment config field 'budgets' must be an array when present")

    raw_models = payload.get("models", [])
    if raw_models is None:
        raw_models = []
    if not isinstance(raw_models, list):
        raise ValueError("experiment config field 'models' must be an array when present")

    raw_backend_overrides = payload.get("backend_overrides", {})
    if not isinstance(raw_backend_overrides, dict):
        raise ValueError("experiment config field 'backend_overrides' must be an object when present")
    raw_project_overrides = payload.get("project_overrides", {})
    if not isinstance(raw_project_overrides, dict):
        raise ValueError("experiment config field 'project_overrides' must be an object when present")

    trial_count = int(payload.get("trial_count", 1))
    if trial_count < 1:
        raise ValueError("experiment config field 'trial_count' must be at least 1")

    results_dir_value = payload.get("results_dir")
    results_dir = _resolve_optional_path(path.parent, results_dir_value)
    return ExperimentSpec(
        config_path=path,
        config_dir=path.parent,
        project_dirs=[_resolve_required_path(path.parent, value) for value in raw_project_dirs],
        backends=[str(value) for value in raw_backends],
        budgets=[int(value) for value in raw_budgets],
        trial_count=trial_count,
        models=[str(value) for value in raw_models],
        results_dir=results_dir,
        backend_overrides=dict(raw_backend_overrides),
        project_overrides=dict(raw_project_overrides),
        raw=dict(payload),
    )


def merge_backend_overrides(
    base: dict[str, Any] | None,
    override: dict[str, Any] | None,
) -> dict[str, Any]:
    merged = dict(base or {})
    for key, value in (override or {}).items():
        if value is not None:
            merged[key] = value
    return merged


def resolve_experiment_inputs(
    *,
    spec: ExperimentSpec | None,
    cli_project_dirs: list[Path],
    cli_backends: list[str] | None,
    cli_budgets: list[int] | None,
    cli_trial_count: int | None,
    cli_models: list[str] | None,
    cli_results_dir: Path | None,
    cli_backend_overrides: dict[str, Any] | None,
) -> dict[str, Any]:
    if spec is None and not cli_project_dirs:
        raise ValueError("provide project directories or --config")

    project_dirs = [path.resolve() for path in cli_project_dirs] if cli_project_dirs else list(spec.project_dirs)
    backends = list(cli_backends or (spec.backends if spec is not None else []))
    if spec is None and not backends:
        backends = ["fake"]
    if not backends:
        raise ValueError("at least one backend is required")

    budgets = list(cli_budgets) if cli_budgets else (list(spec.budgets) if spec is not None else [])
    trial_count = cli_trial_count if cli_trial_count is not None else (spec.trial_count if spec is not None else 1)
    models = list(cli_models) if cli_models else (list(spec.models) if spec is not None else [])
    results_dir = cli_results_dir.resolve() if cli_results_dir is not None else (spec.results_dir if spec is not None else None)
    backend_overrides = merge_backend_overrides(spec.backend_overrides if spec is not None else None, cli_backend_overrides)
    project_overrides = merge_backend_overrides(spec.project_overrides if spec is not None else None, None)

    return {
        "project_dirs": project_dirs,
        "backends": backends,
        "budgets": budgets,
        "trial_count": trial_count,
        "models": models,
        "results_dir": results_dir,
        "backend_overrides": backend_overrides,
        "project_overrides": project_overrides,
        "config_path": spec.config_path if spec is not None else None,
        "config_payload": dict(spec.raw) if spec is not None else None,
    }


def _resolve_required_path(base_dir: Path, value: Any) -> Path:
    text = str(value).strip()
    if not text:
        raise ValueError("experiment config contains an empty path")
    return (base_dir / text).resolve() if not Path(text).is_absolute() else Path(text).resolve()


def _resolve_optional_path(base_dir: Path, value: Any) -> Path | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return (base_dir / text).resolve() if not Path(text).is_absolute() else Path(text).resolve()
