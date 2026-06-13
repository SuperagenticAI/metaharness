import json
import os
import stat
import tempfile
import unittest
from pathlib import Path

from metaharness import EvaluationResult, OmnigentCliBackend, ValidationResult, optimize_harness
from metaharness.reporting import summarize_run


class OmnigentCliBackendTests(unittest.TestCase):
    def test_omnigent_backend_runs_generated_agent_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            baseline = root / "baseline"
            baseline.mkdir()
            (baseline / "target.txt").write_text("before\n", encoding="utf-8")
            fake_omni = root / "fake-omni"
            fake_omni.write_text(
                """#!/usr/bin/env sh
set -eu
printf '%s\n' "$@" > omni-args.txt
printf 'omnigent startup noise\\n' >&2
python3 - <<'PY'
import json
from pathlib import Path
Path("target.txt").write_text("after\\n", encoding="utf-8")
Path(".codex-tmp/private-home").mkdir(parents=True, exist_ok=True)
Path(".codex-tmp/private-home/state.sqlite").write_text("scratch\\n", encoding="utf-8")
events = [
    {"type": "response.output_text.delta", "delta": "working"},
    {
        "type": "response.tool_call.completed",
        "tool_name": "sys_os_write",
        "args": {"path": "target.txt"},
        "usage": {"input_tokens": 10, "output_tokens": 4, "cached_input_tokens": 2},
        "cost_usd": 0.012,
    },
    {"type": "response.completed", "text": "omnigent fake edited target.txt"},
]
Path(".metaharness/omnigent-events.jsonl").write_text(
    "\\n".join(json.dumps(event) for event in events) + "\\n",
    encoding="utf-8",
)
print("omnigent fake edited target.txt")
PY
""",
                encoding="utf-8",
            )
            fake_omni.chmod(fake_omni.stat().st_mode | stat.S_IXUSR)

            class Validator:
                def validate(self, workspace: Path) -> ValidationResult:
                    ok = (workspace / "target.txt").read_text(encoding="utf-8") == "after\n"
                    return ValidationResult(ok=ok, summary="ok" if ok else "not changed")

            class Evaluator:
                def evaluate(self, workspace: Path) -> EvaluationResult:
                    score = 1.0 if (workspace / "target.txt").read_text(encoding="utf-8") == "after\n" else 0.0
                    return EvaluationResult(objective=score, summary="score")

            result = optimize_harness(
                baseline=baseline,
                proposer=OmnigentCliBackend(
                    omnigent_binary=str(fake_omni),
                    harness="codex-native",
                    model="test-model",
                    event_log_path=".metaharness/omnigent-events.jsonl",
                ),
                evaluator=Evaluator(),
                validator=Validator(),
                run_dir=root / "runs" / "omnigent",
                budget=1,
                objective="Edit target.txt.",
                allowed_write_paths=["target.txt", "omni-args.txt"],
            )

            candidate_dir = result.run_dir / "candidates" / "c0001"
            proposal = json.loads((candidate_dir / "proposal" / "result.json").read_text(encoding="utf-8"))
            summary = summarize_run(result.run_dir)
            generated_config = candidate_dir / "proposal" / "omnigent_agent.yaml"
            generated_payload = json.loads(generated_config.read_text(encoding="utf-8"))
            proposal_events = json.loads((candidate_dir / "proposal" / "events.json").read_text(encoding="utf-8"))
            command_args = (candidate_dir / "workspace" / "omni-args.txt").read_text(encoding="utf-8").splitlines()
            runtime_config_dir = candidate_dir / "workspace" / ".metaharness" / "omnigent_agent"
            runtime_config_path = runtime_config_dir / "config.yaml"
            event_log_artifact = candidate_dir / "proposal" / "omnigent_events.jsonl"

            self.assertEqual("c0001", result.best_candidate_id)
            self.assertTrue(generated_config.exists())
            self.assertTrue(runtime_config_path.exists())
            self.assertEqual(".metaharness/AGENTS.md", generated_payload["instructions"])
            self.assertEqual(
                str(candidate_dir / "workspace"),
                generated_payload["os_env"]["cwd"],
            )
            self.assertEqual(
                ["target.txt", "omni-args.txt"],
                generated_payload["os_env"]["sandbox"]["write_paths"],
            )
            self.assertIn("metaharness_enforce_sandbox", generated_payload["policies"])
            self.assertEqual("run", command_args[0])
            self.assertEqual(str(runtime_config_dir), command_args[1])
            self.assertIn("--harness", command_args)
            self.assertIn("codex-native", command_args)
            self.assertIn("--model", command_args)
            self.assertIn("test-model", command_args)
            self.assertIn("--no-session", command_args)
            self.assertTrue(event_log_artifact.exists())
            self.assertTrue(proposal["applied"])
            self.assertEqual("omnigent fake edited target.txt", proposal["final_text"])
            self.assertIn("target.txt", proposal["changed_files"])
            self.assertEqual({"input_tokens": 10, "cached_input_tokens": 2, "output_tokens": 4}, proposal["token_usage"])
            self.assertEqual(0.012, proposal["cost_usd"])
            self.assertEqual(1, proposal["tool_call_count"])
            self.assertEqual({"target.txt": {"writes": 1}}, proposal["files_written"])
            self.assertEqual(4, len(proposal_events))
            self.assertEqual(str(fake_omni), proposal["metadata"]["omnigent_binary"])
            self.assertEqual(str(event_log_artifact), proposal["metadata"]["event_log_artifact_path"])
            self.assertEqual([".codex-tmp"], proposal["metadata"]["cleaned_scratch_paths"])
            self.assertFalse((candidate_dir / "workspace" / ".codex-tmp").exists())
            self.assertFalse(any(".codex-tmp" in path for path in os.listdir(candidate_dir / "workspace")))
            self.assertEqual("omnigent:test-model", summary["backend_label"])


if __name__ == "__main__":
    unittest.main()
