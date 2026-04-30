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
        f"Read the instructions in {instructions_path}.",
        "Inspect .metaharness/experience/parent/ for the parent candidate manifest, validation result, and evaluation result.",
        "Inspect the current workspace, make targeted improvements, and stop when your edits are complete.",
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
