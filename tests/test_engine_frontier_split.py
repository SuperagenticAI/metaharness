import json
import tempfile
import unittest
from pathlib import Path

from metaharness import FakeBackend, optimize_harness
from metaharness.models import EvaluationResult, ValidationResult
from metaharness.reporting import candidate_ledger, summarize_run


class SplitDomainAdapter:
    def validate(self, workspace: Path) -> ValidationResult:
        return ValidationResult(ok=(workspace / "message.txt").exists(), summary="message required")

    def evaluate_search(self, workspace: Path) -> EvaluationResult:
        text = (workspace / "message.txt").read_text(encoding="utf-8")
        if "high-cost" in text:
            return EvaluationResult(
                objective=1.0,
                metrics={"score": 1.0, "context_len": 100.0},
                summary="high score high cost",
            )
        if "low-cost" in text:
            return EvaluationResult(
                objective=1.0,
                metrics={"score": 1.0, "context_len": 10.0},
                summary="high score low cost",
            )
        return EvaluationResult(
            objective=0.0,
            metrics={"score": 0.0, "context_len": 1.0},
            summary="baseline",
        )

    def evaluate_test(self, workspace: Path) -> EvaluationResult | None:
        text = (workspace / "message.txt").read_text(encoding="utf-8")
        score = 0.9 if "low-cost" in text else (0.7 if "high-cost" in text else 0.1)
        return EvaluationResult(objective=score, metrics={"test_score": score}, summary="test evaluation")


class FrontierAndSplitTests(unittest.TestCase):
    def test_frontier_pareto_selects_lower_cost_candidate_and_writes_split_results(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            baseline = root / "baseline"
            baseline.mkdir(parents=True)
            (baseline / "message.txt").write_text("baseline\n", encoding="utf-8")
            run_dir = root / "runs" / "frontier-demo"

            def mutate(request):
                if request.candidate_id.endswith("1"):
                    return {"relative_path": "message.txt", "content": "candidate high-cost\n"}
                return {"relative_path": "message.txt", "content": "candidate low-cost\n"}

            result = optimize_harness(
                baseline=baseline,
                proposer=FakeBackend(mutation=mutate),
                evaluator=None,
                domain_adapter=SplitDomainAdapter(),
                run_dir=run_dir,
                budget=1,
                objective="frontier test",
                search_mode="frontier",
                proposal_batch_size=2,
                selection_policy="pareto",
            )

            self.assertEqual("c0002", result.best_candidate_id)
            best_manifest = json.loads((run_dir / "candidates" / "c0002" / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(1.0, best_manifest["search_objective"])
            self.assertEqual(0.9, best_manifest["test_objective"])
            self.assertEqual(1, best_manifest["frontier_rank"])
            self.assertTrue((run_dir / "candidates" / "c0002" / "evaluation" / "search_result.json").exists())
            self.assertTrue((run_dir / "candidates" / "c0002" / "evaluation" / "test_result.json").exists())

            summary = summarize_run(run_dir)
            self.assertEqual("frontier", summary["search_mode"])
            self.assertEqual("pareto", summary["selection_policy"])
            self.assertEqual(2, summary["proposal_batch_size"])
            self.assertEqual(0.9, summary["best_test_objective"])

            ledger = candidate_ledger(run_dir)
            best_row = next(row for row in ledger if row["candidate_id"] == "c0002")
            self.assertEqual(1.0, best_row["search_objective"])
            self.assertEqual(0.9, best_row["test_objective"])
            self.assertEqual(0, best_row["token_input"])
            self.assertEqual(0, best_row["tool_call_count"])


if __name__ == "__main__":
    unittest.main()
