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
            self.assertEqual(["c0002", "c0000"], result.frontier_candidate_ids)
            best_manifest = json.loads((run_dir / "candidates" / "c0002" / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(1.0, best_manifest["search_objective"])
            self.assertEqual(0.9, best_manifest["test_objective"])
            self.assertEqual(1, best_manifest["frontier_rank"])
            self.assertTrue((run_dir / "candidates" / "c0002" / "evaluation" / "search_result.json").exists())
            self.assertTrue((run_dir / "candidates" / "c0002" / "evaluation" / "test_result.json").exists())
            frontier = json.loads((run_dir / "indexes" / "frontier.json").read_text(encoding="utf-8"))
            self.assertEqual(["c0002", "c0000"], frontier["candidate_ids"])

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

    def test_candidate_prompt_exposes_all_prior_experience_without_test_results(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            baseline = root / "baseline"
            baseline.mkdir(parents=True)
            (baseline / "message.txt").write_text("baseline\n", encoding="utf-8")
            run_dir = root / "runs" / "experience-demo"

            observed_prior_ids = {}
            observed_test_leaks = {}

            def mutate(request):
                experience_dir = request.workspace_dir / ".metaharness" / "experience"
                candidates_dir = experience_dir / "candidates"
                prior_ids = sorted(path.name for path in candidates_dir.iterdir() if path.is_dir())
                observed_prior_ids[request.candidate_id] = prior_ids
                observed_test_leaks[request.candidate_id] = list(candidates_dir.glob("*/evaluation/test_result.json"))
                return {
                    "relative_path": "message.txt",
                    "content": f"candidate {request.candidate_id} low-cost\n",
                }

            result = optimize_harness(
                baseline=baseline,
                proposer=FakeBackend(mutation=mutate),
                evaluator=None,
                domain_adapter=SplitDomainAdapter(),
                run_dir=run_dir,
                budget=2,
                objective="experience test",
            )

            self.assertEqual(["c0000"], observed_prior_ids["c0001"])
            self.assertEqual(["c0000", "c0001"], observed_prior_ids["c0002"])
            self.assertEqual([], observed_test_leaks["c0001"])
            self.assertEqual([], observed_test_leaks["c0002"])

            experience_dir = run_dir / "candidates" / "c0002" / "workspace" / ".metaharness" / "experience"
            self.assertTrue((experience_dir / "index.json").exists())
            self.assertTrue((experience_dir / "README.md").exists())
            self.assertTrue((experience_dir / "candidates" / "c0000" / "workspace" / "message.txt").exists())
            self.assertTrue((experience_dir / "candidates" / "c0001" / "proposal" / "events.json").exists())
            self.assertTrue((run_dir / "candidates" / result.best_candidate_id / "evaluation" / "test_result.json").exists())


if __name__ == "__main__":
    unittest.main()
