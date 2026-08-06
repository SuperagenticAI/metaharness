import json
import tempfile
import unittest
from pathlib import Path

from metaharness import EvaluationResult, FakeBackend, ValidationResult, optimize_harness
from metaharness.models import ProposalExecution, ProposalResult
from metaharness.reporting import summarize_run


class OutcomeValidator:
    def validate(self, workspace: Path) -> ValidationResult:
        exists = (workspace / "message.txt").exists()
        return ValidationResult(ok=exists, summary="message.txt must exist")


class OutcomeEvaluator:
    def evaluate(self, workspace: Path) -> EvaluationResult:
        text = (workspace / "message.txt").read_text(encoding="utf-8")
        score = 1.0 if "better" in text else 0.0
        return EvaluationResult(objective=score, metrics={"score": score}, summary="Outcome evaluator.")


class CrashBackend:
    name = "crash"

    def prepare(self, request):
        return request

    def invoke(self, request) -> ProposalExecution:
        proposal_dir = request.candidate_dir / "proposal"
        proposal_dir.mkdir(parents=True, exist_ok=True)
        stdout_path = proposal_dir / "stdout.jsonl"
        stderr_path = proposal_dir / "stderr.txt"
        stdout_path.write_text("", encoding="utf-8")
        stderr_path.write_text("backend failed\n", encoding="utf-8")
        return ProposalExecution(
            command=["crash-backend"],
            cwd=request.workspace_dir,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            returncode=1,
        )

    def collect(self, execution: ProposalExecution) -> ProposalResult:
        return ProposalResult(
            applied=False,
            summary="Backend crashed.",
            raw_stdout_path=execution.stdout_path,
            raw_stderr_path=execution.stderr_path,
            metadata={"command": execution.command, "returncode": execution.returncode},
        )


class CandidateOutcomeTests(unittest.TestCase):
    def test_reporting_counts_keep_and_discard_outcomes(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            baseline = root / "demo_project" / "baseline"
            baseline.mkdir(parents=True)
            (baseline / "message.txt").write_text("baseline\n", encoding="utf-8")
            run_dir = root / "demo_project" / "runs" / "demo"

            calls = {"count": 0}

            def mutate(request):
                calls["count"] += 1
                if calls["count"] == 1:
                    return {"relative_path": "message.txt", "content": "this is better\n"}
                return {"relative_path": "message.txt", "content": "baseline\n"}

            optimize_harness(
                baseline=baseline,
                proposer=FakeBackend(mutation=mutate),
                validator=OutcomeValidator(),
                evaluator=OutcomeEvaluator(),
                run_dir=run_dir,
                budget=2,
                objective="Exercise keep and discard outcomes.",
            )

            summary = summarize_run(run_dir)
            self.assertEqual(1, summary["keep_candidate_count"])
            self.assertEqual(1, summary["discard_candidate_count"])
            self.assertEqual("keep", summary["best_candidate_outcome"])

    def test_no_change_candidate_gets_explicit_outcome(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            baseline = root / "demo_project" / "baseline"
            baseline.mkdir(parents=True)
            (baseline / "message.txt").write_text("baseline\n", encoding="utf-8")
            run_dir = root / "demo_project" / "runs" / "demo"

            optimize_harness(
                baseline=baseline,
                proposer=FakeBackend(
                    mutation=lambda request: {
                        "relative_path": "message.txt",
                        "content": "baseline\n",
                    }
                ),
                validator=OutcomeValidator(),
                evaluator=OutcomeEvaluator(),
                run_dir=run_dir,
                budget=1,
                objective="Exercise no-change outcome.",
            )

            manifest = json.loads((run_dir / "candidates" / "c0001" / "manifest.json").read_text(encoding="utf-8"))
            summary = summarize_run(run_dir)
            self.assertEqual("no-change", manifest["outcome"])
            self.assertEqual(1, summary["no_change_candidate_count"])

    def test_failed_backend_is_classified_as_crash(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            baseline = root / "demo_project" / "baseline"
            baseline.mkdir(parents=True)
            (baseline / "message.txt").write_text("baseline\n", encoding="utf-8")
            run_dir = root / "demo_project" / "runs" / "demo"

            optimize_harness(
                baseline=baseline,
                proposer=CrashBackend(),
                validator=OutcomeValidator(),
                evaluator=OutcomeEvaluator(),
                run_dir=run_dir,
                budget=1,
                objective="Exercise crash outcome.",
            )

            manifest = json.loads((run_dir / "candidates" / "c0001" / "manifest.json").read_text(encoding="utf-8"))
            summary = summarize_run(run_dir)
            self.assertEqual("crash", manifest["outcome"])
            self.assertEqual(1, summary["crash_candidate_count"])

    def test_scope_violation_candidate_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            baseline = root / "demo_project" / "baseline"
            baseline.mkdir(parents=True)
            (baseline / "message.txt").write_text("baseline\n", encoding="utf-8")
            run_dir = root / "demo_project" / "runs" / "demo"

            optimize_harness(
                baseline=baseline,
                proposer=FakeBackend(
                    mutation=lambda request: {
                        "files": [
                            {"relative_path": "message.txt", "content": "this is better\n"},
                            {"relative_path": "rogue.txt", "content": "not allowed\n"},
                        ]
                    }
                ),
                validator=OutcomeValidator(),
                evaluator=OutcomeEvaluator(),
                run_dir=run_dir,
                budget=1,
                objective="Exercise scope-violation outcome.",
                allowed_write_paths=["message.txt"],
            )

            manifest = json.loads((run_dir / "candidates" / "c0001" / "manifest.json").read_text(encoding="utf-8"))
            summary = summarize_run(run_dir)
            self.assertEqual("scope-violation", manifest["outcome"])
            self.assertEqual(["rogue.txt"], manifest["scope_violation_paths"])
            self.assertEqual(1, summary["scope_violation_candidate_count"])

    def test_runtime_artifacts_do_not_violate_write_scope(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            baseline = root / "demo_project" / "baseline"
            baseline.mkdir(parents=True)
            (baseline / "message.txt").write_text("baseline\n", encoding="utf-8")
            run_dir = root / "demo_project" / "runs" / "demo"

            result = optimize_harness(
                baseline=baseline,
                proposer=FakeBackend(
                    mutation=lambda request: {
                        "files": [
                            {"relative_path": "message.txt", "content": "this is better\n"},
                            {"relative_path": ".venv/bin/python", "content": "runtime shim\n"},
                            {"relative_path": "fixture/__pycache__/module.pyc", "content": "compiled\n"},
                        ]
                    }
                ),
                validator=OutcomeValidator(),
                evaluator=OutcomeEvaluator(),
                run_dir=run_dir,
                budget=1,
                objective="Ignore declared runtime artifacts.",
                allowed_write_paths=["message.txt"],
            )

            manifest = json.loads((run_dir / "candidates" / "c0001" / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual("c0001", result.best_candidate_id)
            self.assertEqual("keep", manifest["outcome"])
            self.assertEqual([], manifest["scope_violation_paths"])


if __name__ == "__main__":
    unittest.main()
