from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class BackendPluginConfig:
    name: str
    factory: str
    options: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class CodingToolTask:
    id: str
    type: str
    weight: float = 1.0
    path: str | None = None
    required_phrases: list[str] = field(default_factory=list)
    command: str | None = None
    expect_exit_code: int = 0


@dataclass(slots=True)
class CodingToolProject:
    root_dir: Path
    objective: str
    constraints: list[str]
    baseline_dir: Path
    runs_dir: Path
    tasks_file: Path
    required_files: list[str]
    test_tasks_file: Path | None = None
    allowed_write_paths: list[str] = field(default_factory=list)
    backend_configs: dict[str, dict[str, Any]] = field(default_factory=dict)
    backend_plugins: dict[str, BackendPluginConfig] = field(default_factory=dict)
    example_profile: str | None = None
    default_budget: int = 1
    tasks: list[CodingToolTask] = field(default_factory=list)
    test_tasks: list[CodingToolTask] = field(default_factory=list)
    search_mode: str = "hill-climb"
    proposal_batch_size: int = 1
    selection_policy: str = "single"


def load_coding_tool_project(project_dir: Path) -> CodingToolProject:
    project_dir = project_dir.resolve()
    config_path = project_dir / "metaharness.json"
    config = _read_json(config_path)
    tasks_file = project_dir / str(config.get("tasks_file", "tasks.json"))
    tasks_payload = json.loads(tasks_file.read_text(encoding="utf-8"))
    tasks = [
        CodingToolTask(
            id=str(item["id"]),
            type=str(item["type"]),
            weight=float(item.get("weight", 1.0)),
            path=item.get("path"),
            required_phrases=[str(value) for value in item.get("required_phrases", [])],
            command=item.get("command"),
            expect_exit_code=int(item.get("expect_exit_code", 0)),
        )
        for item in tasks_payload
    ]
    test_tasks_file = None
    test_tasks: list[CodingToolTask] = []
    if config.get("test_tasks_file") is not None:
        test_tasks_file = project_dir / str(config.get("test_tasks_file"))
        test_tasks_payload = json.loads(test_tasks_file.read_text(encoding="utf-8"))
        test_tasks = [
            CodingToolTask(
                id=str(item["id"]),
                type=str(item["type"]),
                weight=float(item.get("weight", 1.0)),
                path=item.get("path"),
                required_phrases=[str(value) for value in item.get("required_phrases", [])],
                command=item.get("command"),
                expect_exit_code=int(item.get("expect_exit_code", 0)),
            )
            for item in test_tasks_payload
        ]

    return CodingToolProject(
        root_dir=project_dir,
        objective=str(config["objective"]),
        constraints=[str(value) for value in config.get("constraints", [])],
        baseline_dir=project_dir / str(config.get("baseline_dir", "baseline")),
        runs_dir=project_dir / str(config.get("runs_dir", "runs")),
        tasks_file=tasks_file,
        test_tasks_file=test_tasks_file,
        required_files=[str(value) for value in config.get("required_files", [])],
        allowed_write_paths=[str(value) for value in config.get("allowed_write_paths", [])],
        backend_configs=_load_backend_configs(config.get("backends", {})),
        backend_plugins=_load_backend_plugins(config.get("backend_plugins", {})),
        example_profile=config.get("example_profile"),
        default_budget=int(config.get("default_budget", 1)),
        tasks=tasks,
        test_tasks=test_tasks,
        search_mode=str(config.get("search_mode", "hill-climb")),
        proposal_batch_size=int(config.get("proposal_batch_size", 1)),
        selection_policy=str(config.get("selection_policy", "single")),
    )


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_backend_configs(raw_backends: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(raw_backends, dict):
        raise ValueError("metaharness.json field 'backends' must be an object")

    normalized: dict[str, dict[str, Any]] = {}
    for name, config in raw_backends.items():
        if not isinstance(config, dict):
            raise ValueError(f"backend config for {name!r} must be an object")
        normalized[str(name)] = dict(config)
    return normalized


def _load_backend_plugins(raw_plugins: Any) -> dict[str, BackendPluginConfig]:
    if raw_plugins is None:
        return {}
    if not isinstance(raw_plugins, dict):
        raise ValueError("metaharness.json field 'backend_plugins' must be an object")

    normalized: dict[str, BackendPluginConfig] = {}
    for name, raw_config in raw_plugins.items():
        if not isinstance(raw_config, dict):
            raise ValueError(f"backend plugin config for {name!r} must be an object")
        factory = str(raw_config.get("factory", "")).strip()
        if not factory:
            raise ValueError(f"backend plugin {name!r} is missing required field 'factory'")
        options = raw_config.get("options", {})
        if options is None:
            options = {}
        if not isinstance(options, dict):
            raise ValueError(f"backend plugin options for {name!r} must be an object")
        normalized[str(name)] = BackendPluginConfig(
            name=str(name),
            factory=factory,
            options=dict(options),
        )
    return normalized
