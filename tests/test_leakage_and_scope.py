import tempfile
import unittest
from pathlib import Path

from metaharness.core.leakage import collect_leakage_tokens, find_leakage_tokens
from metaharness.core.scope import (
    WriteScopeEntry,
    class_violations,
    infer_write_class,
    parse_allowed_write_paths,
)


class LeakageAndScopeTests(unittest.TestCase):
    def test_infer_write_class_from_common_paths(self) -> None:
        self.assertEqual("prompt", infer_write_class("AGENTS.md"))
        self.assertEqual("prompt", infer_write_class("CLAUDE.md"))
        self.assertEqual("skill", infer_write_class(".agents/skills/repo-hygiene/SKILL.md"))
        self.assertEqual("skill", infer_write_class(".claude/skills/foo/SKILL.md"))
        self.assertEqual("middleware", infer_write_class("scripts/validate.sh"))
        self.assertEqual("memory", infer_write_class("MEMORY.md"))
        self.assertEqual("subagent", infer_write_class(".claude/agents/reviewer.md"))
        self.assertEqual("tool_impl", infer_write_class("tools/search.py"))

    def test_parse_allowed_write_paths_keeps_string_form(self) -> None:
        paths, entries = parse_allowed_write_paths(["AGENTS.md", "scripts"])
        self.assertEqual(["AGENTS.md", "scripts"], paths)
        self.assertEqual(["prompt", "middleware"], [entry.write_class for entry in entries])

    def test_class_violations_require_single_class_mode(self) -> None:
        entries = [
            WriteScopeEntry(path="AGENTS.md", write_class="prompt"),
            WriteScopeEntry(path=".agents/skills", write_class="skill"),
        ]
        changed = ["AGENTS.md", ".agents/skills/repo-hygiene/SKILL.md"]
        self.assertEqual([], class_violations(changed, entries, "all"))
        self.assertEqual(["prompt", "skill"], class_violations(changed, entries, "single-class"))

    def test_collect_leakage_tokens_includes_task_ids_not_phrases(self) -> None:
        tokens = collect_leakage_tokens(
            enabled=True,
            extra=["keyword-dispatch"],
            task_ids=["search-secret-task", "heldout-secret-task"],
        )
        self.assertEqual(
            ["keyword-dispatch", "search-secret-task", "heldout-secret-task"],
            tokens,
        )
        self.assertEqual([], collect_leakage_tokens(enabled=False, extra=["keyword-dispatch"]))

    def test_find_leakage_tokens_skips_metaharness_and_required_body(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            skill = workspace / ".agents" / "skills" / "repo-hygiene" / "SKILL.md"
            skill.parent.mkdir(parents=True)
            skill.write_text("Read the repository before editing.\n", encoding="utf-8")
            leaked = workspace / "AGENTS.md"
            leaked.write_text("do not mention search-secret-task here\n", encoding="utf-8")
            meta = workspace / ".metaharness" / "notes.md"
            meta.parent.mkdir(parents=True)
            meta.write_text("search-secret-task\n", encoding="utf-8")

            found = find_leakage_tokens(
                workspace,
                [
                    ".agents/skills/repo-hygiene/SKILL.md",
                    "AGENTS.md",
                    ".metaharness/notes.md",
                ],
                ["search-secret-task"],
            )
            self.assertEqual(["search-secret-task"], found)


if __name__ == "__main__":
    unittest.main()
