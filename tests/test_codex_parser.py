import tempfile
import unittest
from pathlib import Path

from metaharness.proposer.parsers.codex import parse_codex_jsonl


class CodexParserTests(unittest.TestCase):
    def test_parse_codex_jsonl_extracts_text_commands_and_files(self) -> None:
        payload = "\n".join(
            [
                '{"type":"item.completed","timestamp":"2026-04-01T10:00:00Z","item":{"details":{"text":"thinking"}}}',
                '{"type":"item.completed","timestamp":"2026-04-01T10:00:01Z","item":{"details":{"command":"pytest -q","aggregated_output":"ok"}}}',
                '{"type":"item.completed","timestamp":"2026-04-01T10:00:02Z","item":{"details":{"changes":[{"path":"src/app.py"},{"path":"README.md"}]}}}',
                '{"type":"item.completed","timestamp":"2026-04-01T10:00:03Z","item":{"details":{"text":"final answer"}}}',
            ]
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "stdout.jsonl"
            path.write_text(payload, encoding="utf-8")
            events, final_text, changed_files, telemetry = parse_codex_jsonl(path)

        self.assertEqual(4, len(events))
        self.assertEqual("final answer", final_text)
        self.assertEqual(["src/app.py", "README.md"], changed_files)
        self.assertEqual("pytest -q", events[1].command)
        self.assertIn("token_usage", telemetry)
        self.assertIn("tool_call_count", telemetry)


if __name__ == "__main__":
    unittest.main()
