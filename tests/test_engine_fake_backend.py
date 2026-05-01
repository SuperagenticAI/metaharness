import tempfile
import unittest
import json
from pathlib import Path

from metaharness import EvaluationResult, FakeBackend, ValidationResult, optimize_harness
from metaharness.reporting import candidate_ledger


class SimpleValidator:
    def validate(self, workspace: Path) -> ValidationResult:
        exists = (workspace / "message.txt").exists()
        return ValidationResult(ok=exists, summary="message.txt must exist", metrics={"exists": float(exists)})


class ContainsBetterEvaluator:
    def evaluate(self, workspace: Path) -> EvaluationResult:
        text = (workspace / "message.txt").read_text(encoding="utf-8")
        score = 1.0 if "better" in text else 0.0
        task_fix = "pass" if "better" in text else "fail"
        return EvaluationResult(
            objective=score,
            metrics={"contains_better": score},
            summary="Checks whether the optimized token is present.",
            metadata={"task_results": {"task_fix": task_fix, "task_risk": "pass"}},
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
                        "change_manifest": {
                            "schema_version": "metaharness.change_manifest.v1",
                            "candidate_id": request.candidate_id,
                            "parent_candidate_ids": request.parent_candidate_ids,
                            "changes": [
                                {
                                    "id": "change-1",
                                    "component": "tool_description",
                                    "description": "Clarified the message generation rule.",
                                    "files": ["message.txt"],
                                    "failure_pattern": "task_fix failed without the better token",
                                    "evidence_refs": ["trace_evidence.md"],
                                    "root_cause": "The baseline message was underspecified.",
                                    "targeted_fix": "Include the better token.",
                                    "predicted_fixes": ["task_fix"],
                                    "risk_tasks": ["task_risk"],
                                }
                            ],
                        },
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
            self.assertTrue(manifest["change_manifest_valid"])
            self.assertEqual(1, manifest["change_manifest_change_count"])
            self.assertEqual(["tool_description"], manifest["change_manifest_components"])
            self.assertEqual({"EFFECTIVE": 1}, manifest["change_attribution_verdict_counts"])
            change_manifest = json.loads(
                (run_dir / "candidates" / "c0001" / "proposal" / "change_manifest.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertTrue(change_manifest["validation"]["valid"])
            self.assertEqual("change-1", change_manifest["changes"][0]["id"])
            attribution = json.loads(
                (run_dir / "candidates" / "c0001" / "proposal" / "change_attribution.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(["task_fix"], attribution["task_delta"]["fixed"])
            self.assertEqual("EFFECTIVE", attribution["change_evaluations"][0]["verdict"])
            ledger = candidate_ledger(run_dir)
            row = next(item for item in ledger if item["candidate_id"] == "c0001")
            self.assertTrue(row["change_manifest_valid"])
            self.assertEqual(1, row["change_manifest_change_count"])
            self.assertEqual({"EFFECTIVE": 1}, row["change_attribution_verdict_counts"])
            self.assertEqual("this is better\n", (result.best_workspace_dir / "message.txt").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
