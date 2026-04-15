import os
import subprocess
import tempfile
import unittest
import json
import shutil
from pathlib import Path


class CliTests(unittest.TestCase):
    def test_onboard_command_creates_domain_pack(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmpdir:
            onboarding_dir = Path(tmpdir) / "domain-onboarding"
            env = {**os.environ, "PYTHONPATH": "src"}

            onboard = subprocess.run(
                ["python", "-m", "metaharness.cli", "onboard", str(onboarding_dir)],
                cwd=repo_root,
                env=env,
                text=True,
                capture_output=True,
            )
            self.assertEqual(0, onboard.returncode, onboard.stderr)
            self.assertIn("Created domain onboarding pack", onboard.stdout)
            self.assertTrue((onboarding_dir / "ONBOARDING.md").exists())
            self.assertTrue((onboarding_dir / "domain_spec.md").exists())

            onboarding_text = (onboarding_dir / "ONBOARDING.md").read_text(encoding="utf-8")
            self.assertIn("Required Fields", onboarding_text)
            domain_spec_text = (onboarding_dir / "domain_spec.md").read_text(encoding="utf-8")
            self.assertIn("## Evaluation Plan", domain_spec_text)

    def test_scaffold_and_inspect_flow(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / "coding-tool-project"
            env = {**os.environ, "PYTHONPATH": "src"}

            scaffold = subprocess.run(
                ["python", "-m", "metaharness.cli", "scaffold", "coding-tool", str(project_dir)],
                cwd=repo_root,
                env=env,
                text=True,
                capture_output=True,
            )
            self.assertEqual(0, scaffold.returncode, scaffold.stderr)
            self.assertIn("profile=standard", scaffold.stdout)
            self.assertTrue((project_dir / "metaharness.json").exists())
            self.assertTrue((project_dir / "tasks.json").exists())
            self.assertTrue((project_dir / "baseline" / "AGENTS.md").exists())
            config = json.loads((project_dir / "metaharness.json").read_text(encoding="utf-8"))
            self.assertEqual(["AGENTS.md", "GEMINI.md", "scripts"], config["allowed_write_paths"])

            run = subprocess.run(
                [
                    "python",
                    "-m",
                    "metaharness.cli",
                    "run",
                    str(project_dir),
                    "--backend",
                    "fake",
                    "--budget",
                    "1",
                    "--run-name",
                    "smoke",
                ],
                cwd=repo_root,
                env=env,
                text=True,
                capture_output=True,
            )
            self.assertEqual(0, run.returncode, run.stderr)
            self.assertIn("best_candidate_id=c0001", run.stdout)
            run_dir = project_dir / "runs" / "smoke"
            proposal_result = json.loads(
                (run_dir / "candidates" / "c0001" / "proposal" / "result.json").read_text(encoding="utf-8")
            )
            self.assertEqual(
                {
                    "AGENTS.md",
                    "GEMINI.md",
                    "scripts/bootstrap.sh",
                    "scripts/validate.sh",
                    "scripts/test.sh",
                },
                set(proposal_result["changed_files"]),
            )
            self.assertTrue((run_dir / "candidates" / "c0001" / "proposal" / "workspace.diff").exists())

            inspect = subprocess.run(
                ["python", "-m", "metaharness.cli", "inspect", str(run_dir)],
                cwd=repo_root,
                env=env,
                text=True,
                capture_output=True,
            )
            self.assertEqual(0, inspect.returncode, inspect.stderr)
            self.assertIn("best_candidate_id=c0001", inspect.stdout)

            ledger = subprocess.run(
                ["python", "-m", "metaharness.cli", "ledger", str(run_dir)],
                cwd=repo_root,
                env=env,
                text=True,
                capture_output=True,
            )
            self.assertEqual(0, ledger.returncode, ledger.stderr)
            self.assertIn("candidate_id", ledger.stdout)
            self.assertIn("c0001", ledger.stdout)

            ledger_tsv = subprocess.run(
                ["python", "-m", "metaharness.cli", "ledger", str(run_dir), "--tsv"],
                cwd=repo_root,
                env=env,
                text=True,
                capture_output=True,
            )
            self.assertEqual(0, ledger_tsv.returncode, ledger_tsv.stderr)
            self.assertIn("candidate_id", ledger_tsv.stdout.splitlines()[0])
            self.assertIn("c0001", ledger_tsv.stdout)

            summarize = subprocess.run(
                ["python", "-m", "metaharness.cli", "summarize", str(project_dir)],
                cwd=repo_root,
                env=env,
                text=True,
                capture_output=True,
            )
            self.assertEqual(0, summarize.returncode, summarize.stderr)
            self.assertIn("run_id", summarize.stdout)
            self.assertIn("smoke", summarize.stdout)

            summarize_tsv = subprocess.run(
                ["python", "-m", "metaharness.cli", "summarize", str(project_dir), "--tsv"],
                cwd=repo_root,
                env=env,
                text=True,
                capture_output=True,
            )
            self.assertEqual(0, summarize_tsv.returncode, summarize_tsv.stderr)
            self.assertIn("run_id", summarize_tsv.stdout.splitlines()[0])
            self.assertIn("smoke", summarize_tsv.stdout)

            compare = subprocess.run(
                ["python", "-m", "metaharness.cli", "compare", str(run_dir)],
                cwd=repo_root,
                env=env,
                text=True,
                capture_output=True,
            )
            self.assertEqual(0, compare.returncode, compare.stderr)
            self.assertIn("best_candidate_id=c0001", compare.stdout)
            self.assertIn("backend=fake", compare.stdout)

            compare_tsv = subprocess.run(
                ["python", "-m", "metaharness.cli", "compare", str(run_dir), "--tsv"],
                cwd=repo_root,
                env=env,
                text=True,
                capture_output=True,
            )
            self.assertEqual(0, compare_tsv.returncode, compare_tsv.stderr)
            self.assertIn("run_id", compare_tsv.stdout.splitlines()[0])
            self.assertIn("smoke", compare_tsv.stdout)

    def test_scaffold_local_oss_smoke_profile(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / "coding-tool-project"
            env = {**os.environ, "PYTHONPATH": "src"}

            scaffold = subprocess.run(
                [
                    "python",
                    "-m",
                    "metaharness.cli",
                    "scaffold",
                    "coding-tool",
                    str(project_dir),
                    "--profile",
                    "local-oss-smoke",
                ],
                cwd=repo_root,
                env=env,
                text=True,
                capture_output=True,
            )
            self.assertEqual(0, scaffold.returncode, scaffold.stderr)
            self.assertIn("profile=local-oss-smoke", scaffold.stdout)

            config = json.loads((project_dir / "metaharness.json").read_text(encoding="utf-8"))
            self.assertTrue(config["backends"]["codex"]["use_oss"])
            self.assertEqual("ollama", config["backends"]["codex"]["local_provider"])
            self.assertEqual("gpt-oss:20b", config["backends"]["codex"]["model"])
            self.assertEqual(120, config["backends"]["codex"]["proposal_timeout_seconds"])
            self.assertEqual(["AGENTS.md", "GEMINI.md", "scripts"], config["allowed_write_paths"])
            self.assertTrue((project_dir / "baseline" / "scripts" / "validate.sh").exists())
            self.assertFalse((project_dir / "baseline" / "scripts" / "bootstrap.sh").exists())
            self.assertFalse((project_dir / "baseline" / "scripts" / "test.sh").exists())

    def test_scaffold_local_oss_medium_profile(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / "coding-tool-project"
            env = {**os.environ, "PYTHONPATH": "src"}

            scaffold = subprocess.run(
                [
                    "python",
                    "-m",
                    "metaharness.cli",
                    "scaffold",
                    "coding-tool",
                    str(project_dir),
                    "--profile",
                    "local-oss-medium",
                ],
                cwd=repo_root,
                env=env,
                text=True,
                capture_output=True,
            )
            self.assertEqual(0, scaffold.returncode, scaffold.stderr)
            self.assertIn("profile=local-oss-medium", scaffold.stdout)

            config = json.loads((project_dir / "metaharness.json").read_text(encoding="utf-8"))
            self.assertTrue(config["backends"]["codex"]["use_oss"])
            self.assertEqual("ollama", config["backends"]["codex"]["local_provider"])
            self.assertEqual("gpt-oss:20b", config["backends"]["codex"]["model"])
            self.assertEqual(180, config["backends"]["codex"]["proposal_timeout_seconds"])
            self.assertEqual(["AGENTS.md", "GEMINI.md", "scripts"], config["allowed_write_paths"])
            self.assertTrue((project_dir / "baseline" / "scripts" / "validate.sh").exists())
            self.assertTrue((project_dir / "baseline" / "scripts" / "bootstrap.sh").exists())
            self.assertTrue((project_dir / "baseline" / "scripts" / "test.sh").exists())

            run = subprocess.run(
                [
                    "python",
                    "-m",
                    "metaharness.cli",
                    "run",
                    str(project_dir),
                    "--backend",
                    "fake",
                    "--budget",
                    "1",
                    "--run-name",
                    "medium-fake",
                ],
                cwd=repo_root,
                env=env,
                text=True,
                capture_output=True,
            )
            self.assertEqual(0, run.returncode, run.stderr)
            self.assertIn("best_candidate_id=c0001", run.stdout)

    def test_codex_smoke_probe_only(self) -> None:
        if shutil.which("codex") is None:
            self.skipTest("codex CLI not installed")

        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / "coding-tool-project"
            env = {**os.environ, "PYTHONPATH": "src"}

            scaffold = subprocess.run(
                ["python", "-m", "metaharness.cli", "scaffold", "coding-tool", str(project_dir)],
                cwd=repo_root,
                env=env,
                text=True,
                capture_output=True,
            )
            self.assertEqual(0, scaffold.returncode, scaffold.stderr)

            smoke = subprocess.run(
                [
                    "python",
                    "-m",
                    "metaharness.cli",
                    "smoke",
                    "codex",
                    str(project_dir),
                    "--probe-only",
                ],
                cwd=repo_root,
                env=env,
                text=True,
                capture_output=True,
            )
            self.assertEqual(0, smoke.returncode, smoke.stderr)
            self.assertIn("codex_version=", smoke.stdout)

    def test_smoke_help_lists_all_backends(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        env = {**os.environ, "PYTHONPATH": "src"}

        smoke_help = subprocess.run(
            ["python", "-m", "metaharness.cli", "smoke", "--help"],
            cwd=repo_root,
            env=env,
            text=True,
            capture_output=True,
        )
        self.assertEqual(0, smoke_help.returncode, smoke_help.stderr)
        self.assertIn("{codex,gemini}", smoke_help.stdout)

    def test_experiment_command_writes_results(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / "coding-tool-project"
            results_dir = Path(tmpdir) / "experiment-results"
            env = {**os.environ, "PYTHONPATH": "src"}

            scaffold = subprocess.run(
                ["python", "-m", "metaharness.cli", "scaffold", "coding-tool", str(project_dir)],
                cwd=repo_root,
                env=env,
                text=True,
                capture_output=True,
            )
            self.assertEqual(0, scaffold.returncode, scaffold.stderr)

            experiment = subprocess.run(
                [
                    "python",
                    "-m",
                    "metaharness.cli",
                    "experiment",
                    str(project_dir),
                    "--backend",
                    "fake",
                    "--trials",
                    "2",
                    "--results-dir",
                    str(results_dir),
                ],
                cwd=repo_root,
                env=env,
                text=True,
                capture_output=True,
            )
            self.assertEqual(0, experiment.returncode, experiment.stderr)
            self.assertIn("experiment_dir=", experiment.stdout)
            self.assertTrue((results_dir / "experiment.json").exists())
            self.assertTrue((results_dir / "trials.tsv").exists())
            self.assertTrue((results_dir / "aggregates.tsv").exists())

            experiment_tsv = subprocess.run(
                [
                    "python",
                    "-m",
                    "metaharness.cli",
                    "experiment",
                    str(project_dir),
                    "--backend",
                    "fake",
                    "--trials",
                    "1",
                    "--results-dir",
                    str(Path(tmpdir) / "experiment-results-tsv"),
                    "--tsv",
                ],
                cwd=repo_root,
                env=env,
                text=True,
                capture_output=True,
            )
            self.assertEqual(0, experiment_tsv.returncode, experiment_tsv.stderr)
            self.assertIn("benchmark_name", experiment_tsv.stdout.splitlines()[0])

    def test_experiment_command_accepts_config_file(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            project_dir = root / "coding-tool-project"
            config_path = root / "experiment.json"
            results_dir = root / "config-results"
            env = {**os.environ, "PYTHONPATH": "src"}

            scaffold = subprocess.run(
                ["python", "-m", "metaharness.cli", "scaffold", "coding-tool", str(project_dir)],
                cwd=repo_root,
                env=env,
                text=True,
                capture_output=True,
            )
            self.assertEqual(0, scaffold.returncode, scaffold.stderr)

            config_path.write_text(
                json.dumps(
                    {
                        "project_dirs": ["./coding-tool-project"],
                        "backends": ["fake"],
                        "trial_count": 2,
                        "results_dir": "./config-results",
                    }
                ),
                encoding="utf-8",
            )

            experiment = subprocess.run(
                [
                    "python",
                    "-m",
                    "metaharness.cli",
                    "experiment",
                    "--config",
                    str(config_path),
                ],
                cwd=repo_root,
                env=env,
                text=True,
                capture_output=True,
            )
            self.assertEqual(0, experiment.returncode, experiment.stderr)
            self.assertIn("experiment_dir=", experiment.stdout)
            self.assertTrue((results_dir / "experiment.json").exists())
            self.assertTrue((results_dir / "aggregates.tsv").exists())


if __name__ == "__main__":
    unittest.main()
