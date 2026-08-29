import math
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class EmbedRuntimeTests(unittest.TestCase):
    def test_embed_host_returns_finite_objective(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        script = repo_root / "examples" / "embed_runtime" / "optimize_host.py"
        with tempfile.TemporaryDirectory() as tmpdir:
            completed = subprocess.run(
                [sys.executable, str(script), "--run-dir", tmpdir],
                cwd=repo_root,
                env={**os.environ, "PYTHONPATH": "src"},
                text=True,
                capture_output=True,
            )

        self.assertEqual(0, completed.returncode, completed.stderr)
        self.assertIn("best_candidate_id=", completed.stdout)
        objective = None
        for line in completed.stdout.splitlines():
            if line.startswith("best_objective="):
                objective = float(line.split("=", 1)[1])
                break
        self.assertIsNotNone(objective)
        assert objective is not None
        self.assertTrue(math.isfinite(objective))
        self.assertGreater(objective, 0.0)


if __name__ == "__main__":
    unittest.main()
