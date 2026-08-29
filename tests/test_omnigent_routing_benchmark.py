import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class OmnigentRoutingBenchmarkTests(unittest.TestCase):
    def test_omnigent_routing_benchmark_runs_with_fake_backend(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        example_dir = repo_root / "examples" / "omnigent_routing_benchmark"
        pybin = Path("/tmp/pybin")
        pybin.mkdir(exist_ok=True)
        python_link = pybin / "python"
        if not python_link.exists() and not python_link.is_symlink():
            python_link.symlink_to(sys.executable)

        with tempfile.TemporaryDirectory() as tmpdir:
            run_name = Path(tmpdir).name
            env = {**os.environ, "PYTHONPATH": "src"}
            env["PATH"] = f"{pybin}{os.pathsep}{env.get('PATH', '')}"
            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "metaharness.cli",
                    "run",
                    str(example_dir),
                    "--backend",
                    "fake",
                    "--budget",
                    "1",
                    "--run-name",
                    run_name,
                ],
                cwd=repo_root,
                env=env,
                text=True,
                capture_output=True,
            )

        self.assertEqual(0, completed.returncode, completed.stderr)
        self.assertIn("best_candidate_id=c0001", completed.stdout)
        self.assertIn("best_objective=1.000", completed.stdout)

        run_dir = example_dir / "runs" / run_name
        manifest = json.loads((run_dir / "candidates" / "c0001" / "manifest.json").read_text(encoding="utf-8"))
        self.assertNotEqual("leakage-violation", manifest["outcome"])
        self.assertEqual([], manifest.get("leakage_violation_tokens") or [])

        proposal = json.loads(
            (run_dir / "candidates" / "c0001" / "proposal" / "result.json").read_text(encoding="utf-8")
        )
        changed = [str(path) for path in proposal.get("changed_files", []) if not str(path).startswith(".metaharness")]
        self.assertEqual(["routing.json"], changed)

        workspace_changes = json.loads(
            (run_dir / "candidates" / "c0001" / "proposal" / "workspace_changes.json").read_text(encoding="utf-8")
        )
        self.assertEqual(["routing.json"], [item["path"] for item in workspace_changes])

        routing = (run_dir / "candidates" / "c0001" / "workspace" / "routing.json").read_text(encoding="utf-8")
        for token in ("route-simple", "route-refactor", "route-mid", "heldout-secret-route"):
            self.assertNotIn(token, routing)

        test_result = json.loads(
            (run_dir / "candidates" / "c0001" / "evaluation" / "test_result.json").read_text(encoding="utf-8")
        )
        self.assertGreaterEqual(float(test_result["objective"]), 1.0)


if __name__ == "__main__":
    unittest.main()
