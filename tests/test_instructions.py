import unittest
from pathlib import Path

from metaharness.models import AgentInstructions
from metaharness.proposer.instructions import build_backend_prompt, render_backend_instructions


class InstructionRenderingTests(unittest.TestCase):
    def test_render_codex_instructions_contains_objective(self) -> None:
        text = render_backend_instructions(
            "codex",
            AgentInstructions(
                objective="Improve latency.",
                constraints=["Keep tests passing."],
                workspace_layout="workspace/ holds the harness.",
                allowed_actions=["Edit Python files."],
                forbidden_actions=["Do not touch external artifacts."],
                evaluation_contract="External evaluator decides success.",
            ),
        )
        self.assertIn("Improve latency.", text)
        self.assertIn("Keep tests passing.", text)
        self.assertIn("External evaluator decides success.", text)
        self.assertIn(".metaharness/change_manifest.json", text)
        self.assertIn("predicted_fixes", text)

    def test_build_backend_prompt_embeds_bootstrap_summary(self) -> None:
        prompt = build_backend_prompt(
            "codex",
            Path("/tmp/project/AGENTS.md"),
            Path("/tmp/project"),
            bootstrap_summary_path=Path("/tmp/project/.metaharness/bootstrap/summary.md"),
            bootstrap_summary_text="# Environment Bootstrap\n\n- Working directory: /tmp/project",
        )
        self.assertIn("environment bootstrap", prompt.lower())
        self.assertIn("Working directory: /tmp/project", prompt)

    def test_build_backend_prompt_embeds_trace_evidence(self) -> None:
        prompt = build_backend_prompt(
            "codex",
            Path("/tmp/project/AGENTS.md"),
            Path("/tmp/project"),
            trace_evidence_path=Path("/tmp/project/.metaharness/evidence/trace_evidence.md"),
            trace_evidence_text="# Trace Evidence\n\n- hallucinated tool calls in trace-1",
        )
        self.assertIn("trace evidence report", prompt.lower())
        self.assertIn("hallucinated tool calls in trace-1", prompt)
        self.assertIn(".metaharness/change_manifest.json", prompt)


if __name__ == "__main__":
    unittest.main()
