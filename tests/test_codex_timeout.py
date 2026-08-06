import json
import tempfile
import unittest
from pathlib import Path

from metaharness import EvaluationResult, ValidationResult, optimize_harness
from metaharness.proposer.codex_exec import CodexExecBackend
from metaharness.reporting import summarize_run


class TimeoutValidator:
    def validate(self, workspace: Path) -> ValidationResult:
        exists = (workspace / "message.txt").exists()
        return ValidationResult(ok=exists, summary="message.txt must exist")


class TimeoutEvaluator:
    def evaluate(self, workspace: Path) -> EvaluationResult:
        text = (workspace / "message.txt").read_text(encoding="utf-8")
        score = 1.0 if "better" in text else 0.0
        return EvaluationResult(
            objective=score,
            metrics={"score": score},
            summary="No-op evaluator.",
        )


class CodexTimeoutTests(unittest.TestCase):
    def test_isolated_home_links_auth_and_removes_runtime_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            source_home = Path(tmpdir) / "source-home"
            source_home.mkdir()
            auth_path = source_home / "auth.json"
            auth_path.write_text("{}\n", encoding="utf-8")
            backend = CodexExecBackend(codex_home=str(source_home), isolated_home=True)

            with backend._execution_environment() as environment:
                isolated_home = Path(environment["CODEX_HOME"])
                self.assertNotEqual(source_home, isolated_home)
                self.assertTrue((isolated_home / "auth.json").is_symlink())
                self.assertEqual(auth_path.resolve(), (isolated_home / "auth.json").resolve())
                config = (isolated_home / "config.toml").read_text(encoding="utf-8")
                self.assertIn("hooks = false", config)
                self.assertIn("multi_agent = false", config)
                self.assertTrue(isolated_home.exists())

            self.assertFalse(isolated_home.exists())

    def test_codex_backend_timeout_marks_candidate_failed(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            baseline = root / "baseline"
            baseline.mkdir()
            (baseline / "message.txt").write_text("baseline\n", encoding="utf-8")

            fake_codex = root / "fake-codex"
            fake_codex.write_text(
                "#!/usr/bin/env bash\n"
                "if [[ ${1:-} == --version ]]; then printf 'codex-cli 0.0.0\\n'; exit 0; fi\n"
                "sleep 2\n",
                encoding="utf-8",
            )
            fake_codex.chmod(0o755)

            run_dir = root / "runs" / "timeout"
            result = optimize_harness(
                baseline=baseline,
                proposer=CodexExecBackend(codex_binary=str(fake_codex), timeout_seconds=0.1),
                validator=TimeoutValidator(),
                evaluator=TimeoutEvaluator(),
                run_dir=run_dir,
                budget=1,
                objective="Exercise timeout handling.",
            )

            self.assertEqual("c0000", result.best_candidate_id)
            proposal = json.loads(
                (run_dir / "candidates" / "c0001" / "proposal" / "result.json").read_text(encoding="utf-8")
            )
            manifest = json.loads(
                (run_dir / "candidates" / "c0001" / "manifest.json").read_text(encoding="utf-8")
            )
            self.assertFalse(proposal["applied"])
            self.assertTrue(proposal["metadata"]["timed_out"])
            self.assertEqual(124, proposal["metadata"]["returncode"])
            self.assertIn("timed out", proposal["summary"])
            self.assertEqual("timeout", manifest["outcome"])

    def test_timeout_snapshot_gets_non_selectable_functional_score(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            baseline = root / "baseline"
            baseline.mkdir()
            (baseline / "message.txt").write_text("baseline\n", encoding="utf-8")

            fake_codex = root / "fake-codex"
            fake_codex.write_text(
                "#!/usr/bin/env bash\n"
                "if [[ ${1:-} == --version ]]; then printf 'codex-cli 0.0.0\\n'; exit 0; fi\n"
                "printf 'this is better\\n' > message.txt\n"
                "sleep 2\n",
                encoding="utf-8",
            )
            fake_codex.chmod(0o755)

            run_dir = root / "runs" / "timeout"
            result = optimize_harness(
                baseline=baseline,
                proposer=CodexExecBackend(codex_binary=str(fake_codex), timeout_seconds=0.1),
                validator=TimeoutValidator(),
                evaluator=TimeoutEvaluator(),
                run_dir=run_dir,
                budget=1,
                objective="Exercise timeout shadow evaluation.",
                allowed_write_paths=["message.txt"],
            )

            manifest = json.loads(
                (run_dir / "candidates" / "c0001" / "manifest.json").read_text(encoding="utf-8")
            )
            self.assertEqual("c0000", result.best_candidate_id)
            self.assertEqual("timeout", manifest["outcome"])
            self.assertFalse(manifest["valid"])
            self.assertTrue(manifest["functional_valid"])
            self.assertEqual(1.0, manifest["functional_objective"])
            self.assertFalse(manifest["clean_exit"])
            self.assertTrue(manifest["timed_out"])
            self.assertEqual(124, manifest["proposal_returncode"])
            self.assertGreater(manifest["proposal_duration_seconds"], 0)
            self.assertTrue(
                (run_dir / "candidates" / "c0001" / "shadow_evaluation" / "search_result.json").exists()
            )
            summary = summarize_run(run_dir)
            self.assertEqual("c0001", summary["best_functional_candidate_id"])
            self.assertEqual(1.0, summary["best_functional_objective"])
            self.assertEqual(0, summary["clean_exit_count"])
            self.assertEqual(1, summary["functional_valid_candidate_count"])
            self.assertGreater(summary["mean_proposal_duration_seconds"], 0)


if __name__ == "__main__":
    unittest.main()
