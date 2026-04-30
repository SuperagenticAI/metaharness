from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .experiments import (
    aggregate_tsv_columns,
    default_experiment_dir,
    render_experiment_aggregate_table,
    run_experiment_matrix,
)
from .experiment_config import load_experiment_spec, resolve_experiment_inputs
from .integrations.coding_tool.config import load_coding_tool_project
from .integrations.coding_tool.runtime import resolve_backend_options, run_coding_tool_project
from .proposer.codex_exec import probe_codex_cli, probe_ollama_server
from .proposer.gemini_cli import probe_gemini_cli
from .reporting import (
    candidate_ledger,
    compare_runs,
    ledger_tsv_columns,
    render_candidate_ledger_table,
    render_comparison_table,
    render_run_summary,
    render_tsv,
    summarize_project_runs,
    summarize_run,
    summary_tsv_columns,
)
from .scaffold import create_coding_tool_scaffold, create_domain_onboarding_pack


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="metaharness")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scaffold_parser = subparsers.add_parser("scaffold", help="Create a starter project scaffold.")
    scaffold_parser.add_argument("template", choices=["coding-tool"])
    scaffold_parser.add_argument("target_dir")
    scaffold_parser.add_argument(
        "--profile",
        choices=["standard", "local-oss-smoke", "local-oss-medium"],
        default="standard",
    )

    onboard_parser = subparsers.add_parser("onboard", help="Create a domain onboarding pack.")
    onboard_parser.add_argument("target_dir")

    run_parser = subparsers.add_parser("run", help="Run an optimization project.")
    run_parser.add_argument("project_dir")
    run_parser.add_argument("--backend", default="fake")
    run_parser.add_argument("--budget", type=int, default=None)
    run_parser.add_argument("--run-name", default=None)
    run_parser.add_argument("--hosted", action="store_true")
    run_parser.add_argument("--oss", action="store_true")
    run_parser.add_argument("--local-provider", choices=["ollama", "lmstudio"], default=None)
    run_parser.add_argument("--model", default=None)
    run_parser.add_argument("--proposal-timeout", type=float, default=None)
    run_parser.add_argument("--search-mode", choices=["hill-climb", "frontier"], default=None)
    run_parser.add_argument("--proposal-batch-size", type=int, default=None)
    run_parser.add_argument("--selection-policy", choices=["single", "pareto"], default=None)
    run_parser.add_argument(
        "--trace-evidence",
        default=None,
        help="Path to a HALO/RLM trace evidence markdown report to inject into proposal prompts.",
    )

    experiment_parser = subparsers.add_parser("experiment", help="Run a benchmark x backend x budget x trial matrix.")
    experiment_parser.add_argument("project_dirs", nargs="*")
    experiment_parser.add_argument("--config", default=None)
    experiment_parser.add_argument("--backend", action="append")
    experiment_parser.add_argument("--budget", action="append", type=int, dest="budgets")
    experiment_parser.add_argument("--trials", type=int, default=None)
    experiment_parser.add_argument("--model", action="append", dest="models")
    experiment_parser.add_argument("--results-dir", default=None)
    experiment_parser.add_argument("--json", action="store_true", dest="json_output")
    experiment_parser.add_argument("--tsv", action="store_true", dest="tsv_output")
    experiment_parser.add_argument("--hosted", action="store_true")
    experiment_parser.add_argument("--oss", action="store_true")
    experiment_parser.add_argument("--local-provider", choices=["ollama", "lmstudio"], default=None)
    experiment_parser.add_argument("--proposal-timeout", type=float, default=None)
    experiment_parser.add_argument("--search-mode", choices=["hill-climb", "frontier"], default=None)
    experiment_parser.add_argument("--proposal-batch-size", type=int, default=None)
    experiment_parser.add_argument("--selection-policy", choices=["single", "pareto"], default=None)

    smoke_parser = subparsers.add_parser("smoke", help="Run a backend smoke check.")
    smoke_subparsers = smoke_parser.add_subparsers(dest="smoke_backend", required=True)

    smoke_codex_parser = smoke_subparsers.add_parser("codex", help="Probe and optionally run Codex.")
    smoke_codex_parser.add_argument("project_dir")
    smoke_codex_parser.add_argument("--probe-only", action="store_true")
    smoke_codex_parser.add_argument("--budget", type=int, default=1)
    smoke_codex_parser.add_argument("--run-name", default="codex-smoke")
    smoke_codex_parser.add_argument("--hosted", action="store_true")
    smoke_codex_parser.add_argument("--oss", action="store_true")
    smoke_codex_parser.add_argument("--local-provider", choices=["ollama", "lmstudio"], default=None)
    smoke_codex_parser.add_argument("--model", default=None)
    smoke_codex_parser.add_argument("--proposal-timeout", type=float, default=None)
    smoke_codex_parser.add_argument("--search-mode", choices=["hill-climb", "frontier"], default=None)
    smoke_codex_parser.add_argument("--proposal-batch-size", type=int, default=None)
    smoke_codex_parser.add_argument("--selection-policy", choices=["single", "pareto"], default=None)

    smoke_gemini_parser = smoke_subparsers.add_parser("gemini", help="Probe and optionally run Gemini CLI.")
    smoke_gemini_parser.add_argument("project_dir")
    smoke_gemini_parser.add_argument("--probe-only", action="store_true")
    smoke_gemini_parser.add_argument("--budget", type=int, default=1)
    smoke_gemini_parser.add_argument("--run-name", default="gemini-smoke")
    smoke_gemini_parser.add_argument("--model", default=None)
    smoke_gemini_parser.add_argument("--proposal-timeout", type=float, default=None)
    smoke_gemini_parser.add_argument("--search-mode", choices=["hill-climb", "frontier"], default=None)
    smoke_gemini_parser.add_argument("--proposal-batch-size", type=int, default=None)
    smoke_gemini_parser.add_argument("--selection-policy", choices=["single", "pareto"], default=None)

    inspect_parser = subparsers.add_parser("inspect", help="Inspect a run directory.")
    inspect_parser.add_argument("run_dir")
    inspect_parser.add_argument("--json", action="store_true", dest="json_output")

    ledger_parser = subparsers.add_parser("ledger", help="Export the candidate ledger for one run.")
    ledger_parser.add_argument("run_dir")
    ledger_parser.add_argument("--json", action="store_true", dest="json_output")
    ledger_parser.add_argument("--tsv", action="store_true", dest="tsv_output")

    summarize_parser = subparsers.add_parser("summarize", help="Summarize all runs in a project.")
    summarize_parser.add_argument("project_dir")
    summarize_parser.add_argument("--json", action="store_true", dest="json_output")
    summarize_parser.add_argument("--tsv", action="store_true", dest="tsv_output")

    compare_parser = subparsers.add_parser("compare", help="Compare one or more run directories.")
    compare_parser.add_argument("run_dirs", nargs="+")
    compare_parser.add_argument("--json", action="store_true", dest="json_output")
    compare_parser.add_argument("--tsv", action="store_true", dest="tsv_output")

    args = parser.parse_args(argv)

    if args.command == "scaffold":
        return _cmd_scaffold(args.template, Path(args.target_dir), args.profile)
    if args.command == "onboard":
        return _cmd_onboard(Path(args.target_dir))
    if args.command == "run":
        return _cmd_run(
            project_dir=Path(args.project_dir),
            backend=args.backend,
            budget=args.budget,
            run_name=args.run_name,
            backend_overrides=_backend_overrides_from_args(args),
            project_overrides=_project_overrides_from_args(args),
            trace_evidence_path=Path(args.trace_evidence) if args.trace_evidence else None,
        )
    if args.command == "experiment":
        return _cmd_experiment(
            project_dirs=[Path(value) for value in args.project_dirs],
            config_path=Path(args.config) if args.config else None,
            backends=args.backend,
            budgets=args.budgets,
            trial_count=args.trials,
            models=args.models,
            results_dir=Path(args.results_dir) if args.results_dir else None,
            json_output=args.json_output,
            tsv_output=args.tsv_output,
            backend_overrides=_backend_overrides_from_args(args),
            project_overrides=_project_overrides_from_args(args),
        )
    if args.command == "smoke":
        if args.smoke_backend == "codex":
            return _cmd_smoke_codex(
                project_dir=Path(args.project_dir),
                probe_only=args.probe_only,
                budget=args.budget,
                run_name=args.run_name,
                backend_overrides=_backend_overrides_from_args(args),
                project_overrides=_project_overrides_from_args(args),
            )
        if args.smoke_backend == "gemini":
            return _cmd_smoke_gemini(
                project_dir=Path(args.project_dir),
                probe_only=args.probe_only,
                budget=args.budget,
                run_name=args.run_name,
                backend_overrides=_backend_overrides_from_args(args),
                project_overrides=_project_overrides_from_args(args),
            )
    if args.command == "inspect":
        return _cmd_inspect(Path(args.run_dir), args.json_output)
    if args.command == "ledger":
        return _cmd_ledger(Path(args.run_dir), args.json_output, args.tsv_output)
    if args.command == "summarize":
        return _cmd_summarize(Path(args.project_dir), args.json_output, args.tsv_output)
    if args.command == "compare":
        return _cmd_compare([Path(value) for value in args.run_dirs], args.json_output, args.tsv_output)
    raise RuntimeError(f"unknown command: {args.command}")


def _cmd_scaffold(template: str, target_dir: Path, profile: str) -> int:
    if template != "coding-tool":
        raise ValueError(f"unsupported template: {template}")
    written = create_coding_tool_scaffold(target_dir, profile=profile)
    print(f"Created coding-tool scaffold in {target_dir}")
    print(f"profile={profile}")
    print(f"Wrote {len(written)} files")
    return 0


def _cmd_onboard(target_dir: Path) -> int:
    written = create_domain_onboarding_pack(target_dir)
    print(f"Created domain onboarding pack in {target_dir}")
    print(f"Wrote {len(written)} files")
    return 0


def _cmd_run(
    project_dir: Path,
    backend: str,
    budget: int | None,
    run_name: str | None,
    backend_overrides: dict[str, Any] | None,
    project_overrides: dict[str, Any] | None,
    trace_evidence_path: Path | None,
) -> int:
    project = _load_project(project_dir)
    result = run_coding_tool_project(
        project=project,
        backend_name=backend,
        budget=budget,
        run_name=run_name,
        backend_overrides=backend_overrides,
        trace_evidence_path=trace_evidence_path,
        search_mode=_get_project_override(project_overrides, "search_mode"),
        proposal_batch_size=_get_project_override(project_overrides, "proposal_batch_size"),
        selection_policy=_get_project_override(project_overrides, "selection_policy"),
    )
    print(f"run_dir={result.run_dir}")
    print(f"best_candidate_id={result.best_candidate_id}")
    print(f"best_objective={result.best_objective:.3f}")
    print(f"best_workspace_dir={result.best_workspace_dir}")
    return 0


def _cmd_experiment(
    project_dirs: list[Path],
    config_path: Path | None,
    backends: list[str] | None,
    budgets: list[int] | None,
    trial_count: int | None,
    models: list[str] | None,
    results_dir: Path | None,
    json_output: bool,
    tsv_output: bool,
    backend_overrides: dict[str, Any] | None,
    project_overrides: dict[str, Any] | None,
) -> int:
    spec = load_experiment_spec(config_path) if config_path is not None else None
    resolved = resolve_experiment_inputs(
        spec=spec,
        cli_project_dirs=project_dirs,
        cli_backends=backends,
        cli_budgets=budgets,
        cli_trial_count=trial_count,
        cli_models=models,
        cli_results_dir=results_dir,
        cli_backend_overrides=backend_overrides,
    )

    if resolved["trial_count"] < 1:
        raise SystemExit("--trials must be at least 1")
    resolved_results_dir = resolved["results_dir"] or default_experiment_dir(resolved["project_dirs"][0])
    payload = run_experiment_matrix(
        project_dirs=resolved["project_dirs"],
        backends=resolved["backends"],
        budgets=resolved["budgets"],
        trial_count=resolved["trial_count"],
        models=resolved["models"],
        results_dir=resolved_results_dir,
        backend_overrides=resolved["backend_overrides"],
        project_overrides=project_overrides,
        config_path=resolved["config_path"],
        config_payload=resolved["config_payload"],
    )
    output_mode = _output_mode(json_output, tsv_output)
    if output_mode == "json":
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    if output_mode == "tsv":
        print(render_tsv(payload["aggregates"], aggregate_tsv_columns()))
        return 0

    print(f"experiment_dir={payload['experiment_dir']}")
    print(f"trial_count={len(payload['trials'])}")
    print(f"aggregate_count={len(payload['aggregates'])}")
    print()
    print(render_experiment_aggregate_table(payload["aggregates"]))
    return 0


def _cmd_smoke_codex(
    project_dir: Path,
    probe_only: bool,
    budget: int,
    run_name: str,
    backend_overrides: dict[str, Any] | None,
    project_overrides: dict[str, Any] | None,
) -> int:
    project = _load_project(project_dir)
    resolved_options = resolve_backend_options("codex", project, overrides=backend_overrides)
    probe = probe_codex_cli()
    if not probe["ok"]:
        error = probe.get("error") or "Codex probe failed."
        raise SystemExit(f"Codex unavailable: {error}")

    print(f"codex_binary={probe['resolved_binary']}")
    print(f"codex_version={probe['version'] or 'unknown'}")
    if probe.get("raw_output"):
        print(f"codex_probe_output={probe['raw_output']}")

    use_oss = bool(resolved_options.get("use_oss", False) or resolved_options.get("local_provider"))
    local_provider = resolved_options.get("local_provider")
    model = resolved_options.get("model")
    if use_oss:
        print(f"codex_oss=true")
    if local_provider:
        print(f"codex_local_provider={local_provider}")
    if model:
        print(f"codex_model={model}")
    if resolved_options.get("proposal_timeout_seconds") is not None:
        print(f"codex_proposal_timeout={resolved_options['proposal_timeout_seconds']}")

    if use_oss and local_provider == "ollama":
        ollama_probe = probe_ollama_server()
        if not ollama_probe["ok"]:
            raise SystemExit(f"Ollama unavailable: {ollama_probe['error']}")
        print(f"ollama_base_url={ollama_probe['base_url']}")
        print(f"ollama_version={ollama_probe['version'] or 'unknown'}")
        print(f"ollama_models={','.join(ollama_probe['models'])}")
        if model and model not in ollama_probe["models"]:
            raise SystemExit(f"Configured model not found in Ollama: {model}")

    if probe_only:
        return 0

    result = run_coding_tool_project(
        project=project,
        backend_name="codex",
        budget=budget,
        run_name=run_name,
        backend_overrides=backend_overrides,
        search_mode=_get_project_override(project_overrides, "search_mode"),
        proposal_batch_size=_get_project_override(project_overrides, "proposal_batch_size"),
        selection_policy=_get_project_override(project_overrides, "selection_policy"),
    )
    print(f"run_dir={result.run_dir}")
    print(f"best_candidate_id={result.best_candidate_id}")
    print(f"best_objective={result.best_objective:.3f}")
    print(f"best_workspace_dir={result.best_workspace_dir}")
    return 0


def _cmd_smoke_gemini(
    project_dir: Path,
    probe_only: bool,
    budget: int,
    run_name: str,
    backend_overrides: dict[str, Any] | None,
    project_overrides: dict[str, Any] | None,
) -> int:
    project = _load_project(project_dir)
    resolved_options = resolve_backend_options("gemini", project, overrides=backend_overrides)
    gemini_binary = str(resolved_options.get("gemini_binary") or "gemini")
    probe = probe_gemini_cli(gemini_binary=gemini_binary)
    if not probe["ok"]:
        error = probe.get("error") or "Gemini probe failed."
        raise SystemExit(f"Gemini unavailable: {error}")

    print(f"gemini_binary={probe['resolved_binary']}")
    print(f"gemini_version={probe['version'] or 'unknown'}")
    if probe.get("raw_output"):
        print(f"gemini_probe_output={probe['raw_output']}")
    if resolved_options.get("model"):
        print(f"gemini_model={resolved_options['model']}")
    if resolved_options.get("output_format"):
        print(f"gemini_output_format={resolved_options['output_format']}")
    if resolved_options.get("approval_mode"):
        print(f"gemini_approval_mode={resolved_options['approval_mode']}")
    if resolved_options.get("sandbox") is not None:
        print(f"gemini_sandbox={resolved_options['sandbox']}")
    if resolved_options.get("proposal_timeout_seconds") is not None:
        print(f"gemini_proposal_timeout={resolved_options['proposal_timeout_seconds']}")

    if probe_only:
        return 0

    result = run_coding_tool_project(
        project=project,
        backend_name="gemini",
        budget=budget,
        run_name=run_name,
        backend_overrides=backend_overrides,
        search_mode=_get_project_override(project_overrides, "search_mode"),
        proposal_batch_size=_get_project_override(project_overrides, "proposal_batch_size"),
        selection_policy=_get_project_override(project_overrides, "selection_policy"),
    )
    print(f"run_dir={result.run_dir}")
    print(f"best_candidate_id={result.best_candidate_id}")
    print(f"best_objective={result.best_objective:.3f}")
    print(f"best_workspace_dir={result.best_workspace_dir}")
    return 0


def _cmd_inspect(run_dir: Path, json_output: bool) -> int:
    data = inspect_run(run_dir)
    if json_output:
        print(json.dumps(data, indent=2, sort_keys=True))
        return 0

    print(f"run_dir={data['run_dir']}")
    print(f"run_id={data['run_id']}")
    print(f"best_candidate_id={data['best_candidate_id']}")
    print(f"best_objective={data['best_objective']}")
    print("candidates:")
    for candidate in data["candidates"]:
        print(
            f"  {candidate['candidate_id']}: objective={candidate['objective']} "
            f"valid={candidate['valid']} proposal_applied={candidate['proposal_applied']} "
            f"outcome={candidate.get('outcome', 'unknown')}"
        )
        if candidate.get("scope_violation_paths"):
            print(f"    scope_violation_paths={','.join(candidate['scope_violation_paths'])}")
    return 0


def _cmd_ledger(run_dir: Path, json_output: bool, tsv_output: bool) -> int:
    data = candidate_ledger(run_dir)
    output_mode = _output_mode(json_output, tsv_output)
    if output_mode == "json":
        print(json.dumps(data, indent=2, sort_keys=True))
        return 0
    if output_mode == "tsv":
        print(render_tsv(data, ledger_tsv_columns()))
        return 0

    print(render_candidate_ledger_table(data))
    return 0


def _cmd_summarize(project_dir: Path, json_output: bool, tsv_output: bool) -> int:
    data = summarize_project_runs(project_dir)
    output_mode = _output_mode(json_output, tsv_output)
    if output_mode == "json":
        print(json.dumps(data, indent=2, sort_keys=True))
        return 0
    if output_mode == "tsv":
        print(render_tsv(data, summary_tsv_columns()))
        return 0

    print(render_comparison_table(data))
    return 0


def _cmd_compare(run_dirs: list[Path], json_output: bool, tsv_output: bool) -> int:
    data = compare_runs(run_dirs)
    output_mode = _output_mode(json_output, tsv_output)
    if output_mode == "json":
        print(json.dumps(data, indent=2, sort_keys=True))
        return 0
    if output_mode == "tsv":
        print(render_tsv(data, summary_tsv_columns()))
        return 0

    print(render_comparison_table(data))
    print()
    for summary in data:
        print(render_run_summary(summary))
        print()
    return 0


def inspect_run(run_dir: Path) -> dict[str, Any]:
    run_dir = run_dir.resolve()
    leaderboard = _read_json(run_dir / "indexes" / "leaderboard.json")
    candidates_dir = run_dir / "candidates"
    candidates = []
    if candidates_dir.exists():
        for candidate_dir in sorted(path for path in candidates_dir.iterdir() if path.is_dir()):
            manifest_path = candidate_dir / "manifest.json"
            if not manifest_path.exists():
                continue
            manifest = _read_json(manifest_path)
            candidates.append(manifest)

    candidates.sort(
        key=lambda item: (
            float(item["objective"]) if item.get("objective") is not None else float("-inf"),
            item["candidate_id"],
        ),
        reverse=True,
    )
    return {
        "run_dir": str(run_dir),
        "run_id": run_dir.name,
        "best_candidate_id": leaderboard.get("best_candidate_id"),
        "best_objective": leaderboard.get("best_objective"),
        "candidates": candidates,
    }


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_project(project_dir: Path):
    try:
        return load_coding_tool_project(project_dir)
    except FileNotFoundError as exc:
        missing = exc.filename or str(project_dir / "metaharness.json")
        raise SystemExit(f"Missing project file: {missing}") from exc


def _backend_overrides_from_args(args: argparse.Namespace) -> dict[str, Any] | None:
    if getattr(args, "hosted", False) and getattr(args, "oss", False):
        raise SystemExit("--hosted cannot be combined with --oss")

    if getattr(args, "hosted", False):
        overrides = {
            "use_oss": False,
            "local_provider": "",
            "model": getattr(args, "model", None) if getattr(args, "model", None) is not None else "",
            "proposal_timeout_seconds": getattr(args, "proposal_timeout", None),
        }
        return overrides

    overrides = {
        "use_oss": getattr(args, "oss", None) or None,
        "local_provider": getattr(args, "local_provider", None),
        "model": getattr(args, "model", None),
        "proposal_timeout_seconds": getattr(args, "proposal_timeout", None),
    }
    filtered = {key: value for key, value in overrides.items() if value is not None}
    return filtered or None


def _project_overrides_from_args(args: argparse.Namespace) -> dict[str, Any] | None:
    overrides = {
        "search_mode": getattr(args, "search_mode", None),
        "proposal_batch_size": getattr(args, "proposal_batch_size", None),
        "selection_policy": getattr(args, "selection_policy", None),
    }
    filtered = {key: value for key, value in overrides.items() if value is not None}
    return filtered or None


def _get_project_override(project_overrides: dict[str, Any] | None, key: str):
    if not project_overrides:
        return None
    return project_overrides.get(key)


def _output_mode(json_output: bool, tsv_output: bool) -> str:
    if json_output and tsv_output:
        raise SystemExit("--json cannot be combined with --tsv")
    if json_output:
        return "json"
    if tsv_output:
        return "tsv"
    return "text"


if __name__ == "__main__":
    raise SystemExit(main())
