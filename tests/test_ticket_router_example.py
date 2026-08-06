import os
import subprocess
import tempfile
import unittest
from pathlib import Path


class TicketRouterExampleTests(unittest.TestCase):
    def test_example_runs_with_fake_backend(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        example_dir = repo_root / "examples" / "ticket_router"
        with tempfile.TemporaryDirectory() as tmpdir:
            run_name = str(Path(tmpdir) / "run")
            completed = subprocess.run(
                [
                    "python",
                    str(example_dir / "run.py"),
                    "--backend",
                    "fake",
                    "--budget",
                    "1",
                    "--run-name",
                    run_name,
                ],
                cwd=repo_root,
                env={**os.environ, "PYTHONPATH": "src"},
                text=True,
                capture_output=True,
            )

        self.assertEqual(0, completed.returncode, completed.stderr)
        self.assertIn("best_candidate_id=c0001", completed.stdout)


if __name__ == "__main__":
    unittest.main()
