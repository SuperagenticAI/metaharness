import tempfile
import unittest
import json
from pathlib import Path

from metaharness import EvaluationResult, FakeBackend, ValidationResult, optimize_harness


class SimpleValidator:
    def validate(self, workspace: Path) -> ValidationResult:
        exists = (workspace / "message.txt").exists()
        return ValidationResult(ok=exists, summary="message.txt must exist", metrics={"exists": float(exists)})


class ContainsBetterEvaluator:
    def evaluate(self, workspace: Path) -> EvaluationResult:
        text = (workspace / "message.txt").read_text(encoding="utf-8")
        score = 1.0 if "better" in text else 0.0
        return EvaluationResult(
            objective=score,
            metrics={"contains_better": score},
            summary="Checks whether the optimized token is present.",
        )


class EngineTests(unittest.TestCase):
    def test_engine_improves_candidate_with_fake_backend(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            baseline = root / "baseline"
            baseline.mkdir()
            (baseline / "message.txt").write_text("baseline\n", encoding="utf-8")
            trace_evidence = root / "trace_evidence.md"
            trace_evidence.write_text(
                "# Trace Evidence\n\n- repeated hallucinated tool calls in trace-error\n",
                encoding="utf-8",
            )
            run_dir = root / "runs" / "demo"

            result = optimize_harness(
                baseline=baseline,
                proposer=FakeBackend(
                    mutation=lambda request: {
                        "relative_path": "message.txt",
                        "content": "this is better\n",
                        "summary": f"Improved {request.candidate_id}.",
                    }
                ),
                validator=SimpleValidator(),
                evaluator=ContainsBetterEvaluator(),
                run_dir=run_dir,
                budget=1,
                objective="Make message.txt better.",
                trace_evidence_path=trace_evidence,
            )

            self.assertEqual("c0001", result.best_candidate_id)
            self.assertEqual(1.0, result.best_objective)
            self.assertTrue((run_dir / "indexes" / "leaderboard.json").exists())
            self.assertTrue((run_dir / "candidates" / "c0001" / "proposal" / "workspace.diff").exists())
            bootstrap_summary = (
                run_dir
                / "candidates"
                / "c0001"
                / "workspace"
                / ".metaharness"
                / "bootstrap"
                / "summary.md"
            )
            bootstrap_snapshot = (
                run_dir
                / "candidates"
                / "c0001"
                / "workspace"
                / ".metaharness"
                / "bootstrap"
                / "snapshot.json"
            )
            prompt_path = run_dir / "candidates" / "c0001" / "proposal" / "prompt.txt"
            candidate_evidence = (
                run_dir
                / "candidates"
                / "c0001"
                / "workspace"
                / ".metaharness"
                / "evidence"
                / "trace_evidence.md"
            )
            self.assertTrue(bootstrap_summary.exists())
            self.assertTrue(bootstrap_snapshot.exists())
            self.assertTrue(candidate_evidence.exists())
            self.assertIn("Environment Bootstrap", bootstrap_summary.read_text(encoding="utf-8"))
            prompt = prompt_path.read_text(encoding="utf-8")
            self.assertIn("Working directory", prompt)
            self.assertIn("Trace evidence", prompt)
            self.assertIn("repeated hallucinated tool calls", prompt)
            manifest = json.loads((run_dir / "candidates" / "c0001" / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual("keep", manifest["outcome"])
            self.assertEqual("this is better\n", (result.best_workspace_dir / "message.txt").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
