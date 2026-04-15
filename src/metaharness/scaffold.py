from __future__ import annotations

from pathlib import Path
from textwrap import dedent


def create_coding_tool_scaffold(target_dir: Path, profile: str = "standard") -> list[Path]:
    scaffold_files = build_coding_tool_scaffold(profile)
    written: list[Path] = []
    for relative_path, content in scaffold_files.items():
        path = target_dir / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        if path.suffix == ".sh":
            path.chmod(0o755)
        written.append(path)
    return written


def create_domain_onboarding_pack(target_dir: Path) -> list[Path]:
    files = {
        "ONBOARDING.md": _domain_onboarding_markdown(),
        "domain_spec.md": _domain_spec_template(),
    }
    written: list[Path] = []
    for relative_path, content in files.items():
        path = target_dir / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        written.append(path)
    return written


def build_coding_tool_scaffold(profile: str) -> dict[str, str]:
    if profile == "standard":
        return _standard_scaffold_files()
    if profile == "local-oss-smoke":
        return _local_oss_smoke_scaffold_files()
    if profile == "local-oss-medium":
        return _local_oss_medium_scaffold_files()
    raise ValueError(f"unsupported scaffold profile: {profile}")


def _standard_scaffold_files() -> dict[str, str]:
    return {
        "README.md": _shared_readme(
            profile_name="standard",
            run_codex_command="metaharness run . --backend codex --budget 2",
            extra_guidance=(
                "- configure `backends.codex` in `metaharness.json` if you want hosted Codex or local Codex-over-Ollama"
            ),
        ),
        ".gitignore": _gitignore(),
        "metaharness.json": dedent(
            """\
            {
              "objective": "Improve coding-agent instruction files and helper scripts so the tool behaves safely and predictably.",
              "constraints": [
                "Keep the workflow deterministic.",
                "Focus on AGENTS.md, GEMINI.md, and scripts under baseline/scripts."
              ],
              "baseline_dir": "baseline",
              "runs_dir": "runs",
              "tasks_file": "tasks.json",
              "required_files": [
                "AGENTS.md",
                "GEMINI.md",
                "scripts/bootstrap.sh",
                "scripts/validate.sh",
                "scripts/test.sh"
              ],
              "allowed_write_paths": [
                "AGENTS.md",
                "GEMINI.md",
                "scripts"
              ],
              "backends": {
                "codex": {
                  "sandbox_mode": "workspace-write",
                  "approval_policy": "never",
                  "use_oss": false,
                  "local_provider": null,
                  "model": null,
                  "proposal_timeout_seconds": null
                }
              },
              "example_profile": "coding-tool-scaffold",
              "default_budget": 1,
              "search_mode": "hill-climb",
              "proposal_batch_size": 1,
              "selection_policy": "single",
              "test_tasks_file": null
            }
            """
        ),
        "tasks.json": dedent(
            """\
            [
              {
                "id": "instructions-title",
                "type": "file_phrase",
                "path": "AGENTS.md",
                "weight": 0.5,
                "required_phrases": [
                  "# Project Instructions"
                ]
              },
              {
                "id": "repo-inspection",
                "type": "file_phrase",
                "path": "AGENTS.md",
                "weight": 1.0,
                "required_phrases": [
                  "Read the repository before editing."
                ]
              },
              {
                "id": "git-safety",
                "type": "file_phrase",
                "path": "AGENTS.md",
                "weight": 1.0,
                "required_phrases": [
                  "Never use destructive git commands",
                  "git reset --hard",
                  "git checkout --"
                ]
              },
              {
                "id": "test-guidance",
                "type": "file_phrase",
                "path": "AGENTS.md",
                "weight": 1.0,
                "required_phrases": [
                  "PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q"
                ]
              },
              {
                "id": "workspace-context",
                "type": "file_phrase",
                "path": "GEMINI.md",
                "weight": 1.0,
                "required_phrases": [
                  "Read AGENTS.md first."
                ]
              },
              {
                "id": "feedback-context",
                "type": "file_phrase",
                "path": "GEMINI.md",
                "weight": 1.0,
                "required_phrases": [
                  "Inspect validation and evaluation feedback under .metaharness before editing."
                ]
              },
              {
                "id": "bootstrap-command",
                "type": "command",
                "weight": 1.5,
                "command": "bash scripts/bootstrap.sh",
                "expect_exit_code": 0
              },
              {
                "id": "validate-command",
                "type": "command",
                "weight": 1.5,
                "command": "bash scripts/validate.sh",
                "expect_exit_code": 0
              },
              {
                "id": "test-command",
                "type": "command",
                "weight": 1.5,
                "command": "bash scripts/test.sh",
                "expect_exit_code": 0
              }
            ]
            """
        ),
        **_shared_baseline_files(include_bootstrap=True, include_test=True),
    }


def _local_oss_smoke_scaffold_files() -> dict[str, str]:
    return {
        "README.md": _shared_readme(
            profile_name="local-oss-smoke",
            run_codex_command=(
                "metaharness run . --backend codex --budget 1 "
                "--oss --local-provider ollama --model gpt-oss:20b"
            ),
            extra_guidance=(
                "- this profile is intentionally smaller so a local `gpt-oss:20b` run can finish quickly"
            ),
        ),
        ".gitignore": _gitignore(),
        "metaharness.json": dedent(
            """\
            {
              "objective": "Quickly improve a small coding-agent instruction harness with a fast local OSS smoke suite.",
              "constraints": [
                "Keep the workflow deterministic.",
                "Focus on AGENTS.md, GEMINI.md, and scripts/validate.sh."
              ],
              "baseline_dir": "baseline",
              "runs_dir": "runs",
              "tasks_file": "tasks.json",
              "required_files": [
                "AGENTS.md",
                "GEMINI.md",
                "scripts/validate.sh"
              ],
              "allowed_write_paths": [
                "AGENTS.md",
                "GEMINI.md",
                "scripts"
              ],
              "backends": {
                "codex": {
                  "sandbox_mode": "workspace-write",
                  "approval_policy": "never",
                  "use_oss": true,
                  "local_provider": "ollama",
                  "model": "gpt-oss:20b",
                  "proposal_timeout_seconds": 120
                }
              },
              "example_profile": "coding-tool-scaffold",
              "default_budget": 1,
              "search_mode": "hill-climb",
              "proposal_batch_size": 1,
              "selection_policy": "single",
              "test_tasks_file": null
            }
            """
        ),
        "tasks.json": dedent(
            """\
            [
              {
                "id": "instructions-title",
                "type": "file_phrase",
                "path": "AGENTS.md",
                "weight": 1.0,
                "required_phrases": [
                  "# Project Instructions"
                ]
              },
              {
                "id": "git-safety",
                "type": "file_phrase",
                "path": "AGENTS.md",
                "weight": 1.0,
                "required_phrases": [
                  "Never use destructive git commands",
                  "git reset --hard",
                  "git checkout --"
                ]
              },
              {
                "id": "workspace-context",
                "type": "file_phrase",
                "path": "GEMINI.md",
                "weight": 1.0,
                "required_phrases": [
                  "Read AGENTS.md first.",
                  "Inspect validation and evaluation feedback under .metaharness before editing."
                ]
              },
              {
                "id": "validate-command",
                "type": "command",
                "weight": 2.0,
                "command": "bash scripts/validate.sh",
                "expect_exit_code": 0
              }
            ]
            """
        ),
        **_shared_baseline_files(include_bootstrap=False, include_test=False),
    }


def _local_oss_medium_scaffold_files() -> dict[str, str]:
    return {
        "README.md": _shared_readme(
            profile_name="local-oss-medium",
            run_codex_command=(
                "metaharness run . --backend codex --budget 1 "
                "--oss --local-provider ollama --model gpt-oss:20b --proposal-timeout 180"
            ),
            extra_guidance=(
                "- this profile restores bootstrap and test scripts while staying smaller than the full standard scaffold"
            ),
        ),
        ".gitignore": _gitignore(),
        "metaharness.json": dedent(
            """\
            {
              "objective": "Improve a medium-size coding-agent instruction harness with local OSS Codex over Ollama.",
              "constraints": [
                "Keep the workflow deterministic.",
                "Focus on AGENTS.md, GEMINI.md, and scripts/bootstrap.sh, scripts/validate.sh, scripts/test.sh."
              ],
              "baseline_dir": "baseline",
              "runs_dir": "runs",
              "tasks_file": "tasks.json",
              "required_files": [
                "AGENTS.md",
                "GEMINI.md",
                "scripts/bootstrap.sh",
                "scripts/validate.sh",
                "scripts/test.sh"
              ],
              "allowed_write_paths": [
                "AGENTS.md",
                "GEMINI.md",
                "scripts"
              ],
              "backends": {
                "codex": {
                  "sandbox_mode": "workspace-write",
                  "approval_policy": "never",
                  "use_oss": true,
                  "local_provider": "ollama",
                  "model": "gpt-oss:20b",
                  "proposal_timeout_seconds": 180
                }
              },
              "example_profile": "coding-tool-scaffold",
              "default_budget": 1,
              "search_mode": "hill-climb",
              "proposal_batch_size": 1,
              "selection_policy": "single",
              "test_tasks_file": null
            }
            """
        ),
        "tasks.json": dedent(
            """\
            [
              {
                "id": "instructions-title",
                "type": "file_phrase",
                "path": "AGENTS.md",
                "weight": 0.5,
                "required_phrases": [
                  "# Project Instructions"
                ]
              },
              {
                "id": "git-safety",
                "type": "file_phrase",
                "path": "AGENTS.md",
                "weight": 1.0,
                "required_phrases": [
                  "Never use destructive git commands",
                  "git reset --hard",
                  "git checkout --"
                ]
              },
              {
                "id": "test-guidance",
                "type": "file_phrase",
                "path": "AGENTS.md",
                "weight": 1.0,
                "required_phrases": [
                  "PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q"
                ]
              },
              {
                "id": "workspace-context",
                "type": "file_phrase",
                "path": "GEMINI.md",
                "weight": 1.0,
                "required_phrases": [
                  "Read AGENTS.md first.",
                  "Inspect validation and evaluation feedback under .metaharness before editing."
                ]
              },
              {
                "id": "bootstrap-command",
                "type": "command",
                "weight": 1.5,
                "command": "bash scripts/bootstrap.sh",
                "expect_exit_code": 0
              },
              {
                "id": "validate-command",
                "type": "command",
                "weight": 1.5,
                "command": "bash scripts/validate.sh",
                "expect_exit_code": 0
              },
              {
                "id": "test-command",
                "type": "command",
                "weight": 1.5,
                "command": "bash scripts/test.sh",
                "expect_exit_code": 0
              }
            ]
            """
        ),
        **_shared_baseline_files(include_bootstrap=True, include_test=True),
    }


def _shared_readme(profile_name: str, run_codex_command: str, extra_guidance: str) -> str:
    return dedent(
        f"""\
        # Coding Tool Optimization Scaffold

        This scaffold is meant for two use cases:

        1. developers building agentic coding systems
        2. advanced users tuning AGENTS.md, GEMINI.md, and helper scripts around coding-agent tools

        The baseline workspace lives under `baseline/`.
        The project is configured by `metaharness.json`.
        This scaffold was generated with the `{profile_name}` profile.

        Run it with the fake backend:

        ```bash
        metaharness run . --backend fake --budget 1
        ```

        Run it with Codex:

        ```bash
        {run_codex_command}
        ```

        Probe the local Codex CLI before spending model calls:

        ```bash
        metaharness smoke codex . --probe-only
        ```

        To adapt this scaffold to your real workflow:

        - edit `metaharness.json` to define the objective, constraints, required files, and `allowed_write_paths`
        {extra_guidance}
        - replace `tasks.json` with deterministic `file_phrase` and `command` checks that match your workflow
        - expand `baseline/AGENTS.md`, `baseline/GEMINI.md`, and `baseline/scripts/`
        - replace the placeholder command checks in `baseline/scripts/` with real bootstrap and validation logic
        """
    )


def _gitignore() -> str:
    return dedent(
        """\
        __pycache__/
        *.pyc
        runs/
        """
    )


def _shared_baseline_files(include_bootstrap: bool, include_test: bool) -> dict[str, str]:
    files = {
        "baseline/AGENTS.md": dedent(
            """\
            # Project Instructions

            - Be concise.
            - Check the repository before editing.
            - Run tests when possible.
            """
        ),
        "baseline/GEMINI.md": dedent(
            """\
            # Project Context

            Use the current workspace carefully and keep changes small.
            """
        ),
        "baseline/scripts/validate.sh": dedent(
            """\
            #!/usr/bin/env bash
            set -euo pipefail

            echo "validate placeholder"
            exit 1
            """
        ),
    }
    if include_bootstrap:
        files["baseline/scripts/bootstrap.sh"] = dedent(
            """\
            #!/usr/bin/env bash
            set -euo pipefail

            echo "bootstrap placeholder"
            exit 1
            """
        )
    if include_test:
        files["baseline/scripts/test.sh"] = dedent(
            """\
            #!/usr/bin/env bash
            set -euo pipefail

            echo "test placeholder"
            exit 1
            """
        )
    return files


def _domain_onboarding_markdown() -> str:
    return dedent(
        """\
        # MetaHarness Domain Onboarding

        Use this file when adapting `metaharness` to a new domain.
        The goal is to produce a concrete `domain_spec.md` before implementing adapters or benchmark code.

        ## Rules

        - Do not start implementation until all required fields are filled or marked `unknown`.
        - Ask focused questions, one or two at a time.
        - Prefer concrete numbers for budget, runtime, and dataset sizes.
        - Call out evaluation leakage risks explicitly.
        - Keep base model and tool surface fixed during the first pass unless there is a strong reason not to.

        ## Required Fields

        1. Problem framing:
        - What are we trying to improve?
        - What is one unit of evaluation?
        - What is fixed vs mutable?
        - What model is fixed during optimization?
        - What budget can we spend (time, cost, candidates, or tokens)?

        2. Harness definition:
        - What interface must every candidate harness satisfy?
        - How do we validate interface compliance?
        - What changes are out of scope?

        3. Evaluation:
        - What is the search-set evaluation?
        - What is the held-out test evaluation?
        - What primary and secondary metrics matter?
        - How noisy is the signal and what is one candidate runtime?
        - What contamination risks exist and how are they mitigated?

        4. Baselines:
        - Which hand-written baselines should be included?
        - What is the current strongest baseline?

        5. Experience artifacts:
        - Which offline traces or documents should seed search?
        - Which online artifacts must be stored per candidate?
        - Which files are highest signal for debugging regressions?

        ## Suggested Workflow

        1. Gather missing information and record assumptions in `domain_spec.md`.
        2. Define search and test splits before writing code.
        3. Implement one deterministic baseline harness first.
        4. Add validation checks and objective scoring.
        5. Run short fake or smoke loops before expensive provider runs.
        """
    )


def _domain_spec_template() -> str:
    return dedent(
        """\
        # Domain Spec: <replace-with-domain-name>

        ## Domain Summary

        - Goal:
        - Unit of evaluation:
        - Fixed components:
        - Mutable harness surface:
        - Fixed model(s):
        - Optimization budget:

        ## Harness Interface

        - Candidate harness contract:
        - Required inputs and outputs:
        - Validation gate:
        - Out-of-scope changes:

        ## Evaluation Plan

        - Search-set dataset:
        - Held-out test dataset:
        - Primary metric:
        - Secondary metrics:
        - Runtime per candidate:
        - Noise considerations:
        - Leakage or contamination risks:

        ## Baselines

        - Baseline A:
        - Baseline B:
        - Strongest known baseline:

        ## Experience and Logging

        - Offline traces:
        - Online per-candidate artifacts:
        - Required metadata:
        - Run directory layout notes:

        ## Open Questions

        - Unknowns:
        - Risky assumptions:
        - Next validation step:
        """
    )
