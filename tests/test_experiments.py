import tempfile
import unittest
from pathlib import Path

from metaharness.experiment_config import load_experiment_spec, resolve_experiment_inputs
from metaharness.experiments import aggregate_experiment_trials, run_experiment_matrix
from metaharness.scaffold import create_coding_tool_scaffold


class ExperimentTests(unittest.TestCase):
    def test_load_experiment_spec_resolves_relative_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            project_dir = root / "project"
            project_dir.mkdir()
            config_path = root / "matrix.json"
            config_path.write_text(
                """
                {
                  "project_dirs": ["./project"],
                  "backends": ["fake"],
                  "budgets": [1, 2],
                  "trial_count": 3,
                  "results_dir": "./results"
                }
                """.strip(),
                encoding="utf-8",
            )

            spec = load_experiment_spec(config_path)
            resolved = resolve_experiment_inputs(
                spec=spec,
                cli_project_dirs=[],
                cli_backends=None,
                cli_budgets=None,
                cli_trial_count=None,
                cli_models=None,
                cli_results_dir=None,
                cli_backend_overrides=None,
            )

            self.assertEqual([project_dir.resolve()], spec.project_dirs)
            self.assertEqual((root / "results").resolve(), spec.results_dir)
            self.assertEqual([project_dir.resolve()], resolved["project_dirs"])
            self.assertEqual(["fake"], resolved["backends"])
            self.assertEqual([1, 2], resolved["budgets"])
            self.assertEqual(3, resolved["trial_count"])

    def test_run_experiment_matrix_writes_trial_and_aggregate_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            project_dir = root / "project"
            create_coding_tool_scaffold(project_dir, profile="standard")
            results_dir = root / "experiment-results"

            payload = run_experiment_matrix(
                project_dirs=[project_dir],
                backends=["fake"],
                budgets=[1],
                trial_count=2,
                results_dir=results_dir,
            )

            self.assertEqual(str(results_dir.resolve()), payload["experiment_dir"])
            self.assertEqual(2, len(payload["trials"]))
            self.assertEqual(1, len(payload["aggregates"]))
            self.assertTrue((results_dir / "experiment.json").exists())
            self.assertTrue((results_dir / "trials.json").exists())
            self.assertTrue((results_dir / "aggregates.json").exists())
            self.assertTrue((results_dir / "trials.tsv").exists())
            self.assertTrue((results_dir / "aggregates.tsv").exists())

            aggregate = payload["aggregates"][0]
            self.assertEqual("project", aggregate["benchmark_name"])
            self.assertEqual("fake", aggregate["backend_label"])
            self.assertEqual(2, aggregate["trial_count"])
            self.assertEqual(1.0, aggregate["success_rate"])

            trials_tsv = (results_dir / "trials.tsv").read_text(encoding="utf-8")
            aggregates_tsv = (results_dir / "aggregates.tsv").read_text(encoding="utf-8")
            self.assertIn("trial_index", trials_tsv.splitlines()[0])
            self.assertIn("benchmark_name", aggregates_tsv.splitlines()[0])

    def test_aggregate_experiment_trials_computes_rates(self) -> None:
        aggregates = aggregate_experiment_trials(
            [
                {
                    "benchmark_name": "bench",
                    "backend": "codex",
                    "backend_label": "codex:model-a",
                    "model": "model-a",
                    "budget": 1,
                    "improved": True,
                    "best_objective": 1.0,
                    "best_functional_objective": 1.0,
                    "mean_proposal_duration_seconds": 8.0,
                    "clean_exit_count": 1,
                    "functional_valid_candidate_count": 1,
                    "duration_seconds": 10.0,
                    "time_to_first_improvement_seconds": 3.0,
                    "keep_candidate_count": 1,
                    "timeout_candidate_count": 0,
                    "crash_candidate_count": 0,
                    "scope_violation_candidate_count": 0,
                },
                {
                    "benchmark_name": "bench",
                    "backend": "codex",
                    "backend_label": "codex:model-a",
                    "model": "model-a",
                    "budget": 1,
                    "improved": False,
                    "best_objective": 0.5,
                    "best_functional_objective": 0.8,
                    "mean_proposal_duration_seconds": 18.0,
                    "clean_exit_count": 0,
                    "functional_valid_candidate_count": 1,
                    "duration_seconds": 20.0,
                    "time_to_first_improvement_seconds": None,
                    "keep_candidate_count": 0,
                    "timeout_candidate_count": 1,
                    "crash_candidate_count": 0,
                    "scope_violation_candidate_count": 1,
                },
            ]
        )

        self.assertEqual(1, len(aggregates))
        aggregate = aggregates[0]
        self.assertEqual(2, aggregate["trial_count"])
        self.assertEqual(1, aggregate["improved_count"])
        self.assertEqual(0.5, aggregate["success_rate"])
        self.assertEqual(0.75, aggregate["mean_best_objective"])
        self.assertEqual(0.9, aggregate["mean_best_functional_objective"])
        self.assertEqual(13.0, aggregate["mean_proposal_duration_seconds"])
        self.assertEqual(0.5, aggregate["clean_exit_run_rate"])
        self.assertEqual(1.0, aggregate["functional_valid_run_rate"])
        self.assertEqual(0.5, aggregate["timeout_run_rate"])
        self.assertEqual(0.5, aggregate["scope_violation_run_rate"])


if __name__ == "__main__":
    unittest.main()
