from __future__ import annotations

from pathlib import Path

from ..models import AgentInstructions


def render_backend_instructions(proposer_name: str, instructions: AgentInstructions) -> str:
    if proposer_name == "codex":
        return render_codex_instructions(instructions)
    if proposer_name == "gemini":
        return render_gemini_instructions(instructions)
    return render_generic_instructions(instructions)


def render_codex_instructions(instructions: AgentInstructions) -> str:
    body = [
        "# MetaHarness Candidate Instructions",
        "",
        "## Objective",
        instructions.objective,
        "",
        "## Constraints",
    ]
    body.extend(f"- {item}" for item in instructions.constraints or ["None"])
    body.extend(
        [
            "",
            "## Workspace Layout",
            instructions.workspace_layout or "No workspace notes provided.",
            "",
            "## Allowed Actions",
        ]
    )
    body.extend(f"- {item}" for item in instructions.allowed_actions or ["Use normal engineering judgment."])
    body.extend(
        [
            "",
            "## Forbidden Actions",
        ]
    )
    body.extend(f"- {item}" for item in instructions.forbidden_actions or ["None"])
    body.extend(
        [
            "",
            "## Evaluation Contract",
            instructions.evaluation_contract or "External validation and evaluation decide success.",
            "",
            "## Change Manifest",
            _change_manifest_instructions(),
            "",
        ]
    )
    return "\n".join(body)


def render_gemini_instructions(instructions: AgentInstructions) -> str:
    body = [
        "# MetaHarness Project Context",
        "",
        "## Objective",
        instructions.objective,
        "",
        "## Constraints",
    ]
    body.extend(f"- {item}" for item in instructions.constraints or ["None"])
    body.extend(
        [
            "",
            "## Workspace Layout",
            instructions.workspace_layout or "No workspace notes provided.",
            "",
            "## Allowed Actions",
        ]
    )
    body.extend(f"- {item}" for item in instructions.allowed_actions or ["Use normal engineering judgment."])
    body.extend(
        [
            "",
            "## Forbidden Actions",
        ]
    )
    body.extend(f"- {item}" for item in instructions.forbidden_actions or ["None"])
    body.extend(
        [
            "",
            "## Evaluation Contract",
            instructions.evaluation_contract or "External validation and evaluation decide success.",
            "",
            "## Change Manifest",
            _change_manifest_instructions(),
            "",
        ]
    )
    return "\n".join(body)


def render_generic_instructions(instructions: AgentInstructions) -> str:
    return render_codex_instructions(instructions)


def build_backend_prompt(
    proposer_name: str,
    instructions_path: Path,
    workspace_dir: Path,
    *,
    bootstrap_summary_path: Path | None = None,
    bootstrap_summary_text: str = "",
    trace_evidence_path: Path | None = None,
    trace_evidence_text: str = "",
) -> str:
    prompt = [
        f"You are optimizing a harness candidate inside {workspace_dir}.",
        f"Current candidate id: {workspace_dir.parent.name}.",
        f"Read the instructions in {instructions_path}.",
        "Inspect .metaharness/experience/parent/ for the parent candidate manifest, validation result, and evaluation result.",
        "Inspect the current workspace, make targeted improvements, and stop when your edits are complete.",
        "Before finishing, write .metaharness/change_manifest.json describing each harness change and its predicted impact.",
        "Do not claim success without making concrete changes.",
    ]
    if bootstrap_summary_path is not None:
        prompt.append(
            f"Use the environment bootstrap in {bootstrap_summary_path} before spending turns on basic workspace discovery."
        )
    if trace_evidence_path is not None:
        prompt.append(
            f"Use the trace evidence report in {trace_evidence_path} to ground harness changes in observed failures."
        )
    if proposer_name == "codex":
        prompt.append("Follow the instructions file carefully before editing.")
    if proposer_name == "gemini":
        prompt.append("Use the project context file before proposing changes.")
    if bootstrap_summary_text.strip():
        prompt.extend(["", "Environment bootstrap:", "", bootstrap_summary_text.strip()])
    if trace_evidence_text.strip():
        prompt.extend(["", "Trace evidence:", "", trace_evidence_text.strip()])
    return "\n".join(prompt)


def _change_manifest_instructions() -> str:
    return """Before finishing, write `.metaharness/change_manifest.json`.

Use this JSON shape:

```json
{
  "schema_version": "metaharness.change_manifest.v1",
  "candidate_id": "<candidate id if known>",
  "parent_candidate_ids": ["<parent id>"],
  "changes": [
    {
      "id": "change-1",
      "component": "system_prompt | tool | tool_description | middleware | skill | memory | evaluator | orchestration | docs | other",
      "description": "What changed.",
      "files": ["relative/path.py"],
      "failure_pattern": "Observed failure pattern this addresses.",
      "evidence_refs": ["trace_evidence.md#section", "task-or-trace-id"],
      "root_cause": "Why the previous harness failed.",
      "targeted_fix": "Why this edit should fix it.",
      "predicted_fixes": ["task-id-expected-to-improve"],
      "risk_tasks": ["task-id-at-risk-of-regression"],
      "notes": "Optional implementation notes."
    }
  ]
}
```

Keep entries evidence-backed. Use empty arrays for `predicted_fixes` or `risk_tasks` when task-level ids are unavailable."""
