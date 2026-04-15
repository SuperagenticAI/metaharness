import tempfile
import unittest
import sys
from pathlib import Path
from unittest.mock import patch

from metaharness.integrations.coding_tool.config import load_coding_tool_project
from metaharness.integrations.coding_tool.runtime import _resolve_command_shell, make_backend, resolve_backend_options
from metaharness.proposer.fake import FakeBackend


class CodingToolConfigTests(unittest.TestCase):
    def test_load_project_reads_search_and_split_settings(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "baseline").mkdir()
            (root / "tasks.json").write_text(
                '[{"id":"search-1","type":"file_phrase","path":"AGENTS.md","required_phrases":["x"]}]',
                encoding="utf-8",
            )
            (root / "tasks_test.json").write_text(
                '[{"id":"test-1","type":"file_phrase","path":"AGENTS.md","required_phrases":["y"]}]',
                encoding="utf-8",
            )
            (root / "metaharness.json").write_text(
                """
                {
                  "objective": "demo",
                  "constraints": [],
                  "required_files": [],
                  "tasks_file": "tasks.json",
                  "test_tasks_file": "tasks_test.json",
                  "search_mode": "frontier",
                  "proposal_batch_size": 3,
                  "selection_policy": "pareto",
                  "backends": {}
                }
                """.strip(),
                encoding="utf-8",
            )

            project = load_coding_tool_project(root)
            self.assertEqual("frontier", project.search_mode)
            self.assertEqual(3, project.proposal_batch_size)
            self.assertEqual("pareto", project.selection_policy)
            self.assertEqual(1, len(project.tasks))
            self.assertEqual(1, len(project.test_tasks))

    def test_make_backend_applies_codex_backend_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "baseline").mkdir()
            (root / "tasks.json").write_text("[]", encoding="utf-8")
            (root / "metaharness.json").write_text(
                """
                {
                  "objective": "demo",
                  "constraints": [],
                  "required_files": [],
                  "backends": {
                    "codex": {
                      "use_oss": true,
                      "local_provider": "ollama",
                      "model": "gpt-oss:20b",
                      "approval_policy": "never",
                      "sandbox_mode": "workspace-write"
                    }
                  }
                }
                """.strip(),
                encoding="utf-8",
            )

            project = load_coding_tool_project(root)
            backend = make_backend("codex", project)

            self.assertTrue(backend.use_oss)
            self.assertEqual("ollama", backend.local_provider)
            self.assertEqual("gpt-oss:20b", backend.model)
            self.assertIsNone(backend.timeout_seconds)
            self.assertEqual([], project.allowed_write_paths)

    def test_make_backend_can_override_local_codex_config_to_hosted(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "baseline").mkdir()
            (root / "tasks.json").write_text("[]", encoding="utf-8")
            (root / "metaharness.json").write_text(
                """
                {
                  "objective": "demo",
                  "constraints": [],
                  "required_files": [],
                  "backends": {
                    "codex": {
                      "use_oss": true,
                      "local_provider": "ollama",
                      "model": "gpt-oss:20b",
                      "approval_policy": "never",
                      "sandbox_mode": "workspace-write"
                    }
                  }
                }
                """.strip(),
                encoding="utf-8",
            )

            project = load_coding_tool_project(root)
            backend = make_backend(
                "codex",
                project,
                overrides={"use_oss": False, "local_provider": "", "model": ""},
            )

            self.assertFalse(backend.use_oss)
            self.assertIsNone(backend.local_provider)
            self.assertIsNone(backend.model)

    def test_load_project_reads_allowed_write_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "baseline").mkdir()
            (root / "tasks.json").write_text("[]", encoding="utf-8")
            (root / "metaharness.json").write_text(
                """
                {
                  "objective": "demo",
                  "constraints": [],
                  "required_files": [],
                  "allowed_write_paths": ["AGENTS.md", "scripts"],
                  "backends": {}
                }
                """.strip(),
                encoding="utf-8",
            )

            project = load_coding_tool_project(root)
            self.assertEqual(["AGENTS.md", "scripts"], project.allowed_write_paths)

    def test_make_backend_applies_gemini_backend_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "baseline").mkdir()
            (root / "tasks.json").write_text("[]", encoding="utf-8")
            (root / "metaharness.json").write_text(
                """
                {
                  "objective": "demo",
                  "constraints": [],
                  "required_files": [],
                  "backends": {
                    "gemini": {
                      "gemini_binary": "gemini",
                      "model": "gemini-2.5-pro",
                      "output_format": "stream-json",
                      "approval_mode": "default",
                      "sandbox": "workspace-write",
                      "proposal_timeout_seconds": 45
                    }
                  }
                }
                """.strip(),
                encoding="utf-8",
            )

            project = load_coding_tool_project(root)
            backend = make_backend("gemini", project)

            self.assertEqual("gemini", backend.gemini_binary)
            self.assertEqual("gemini-2.5-pro", backend.model)
            self.assertEqual("stream-json", backend.output_format)
            self.assertEqual("default", backend.approval_mode)
            self.assertEqual("workspace-write", backend.sandbox)
            self.assertEqual(45.0, backend.timeout_seconds)

    def test_load_project_reads_backend_plugins(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "baseline").mkdir()
            (root / "tasks.json").write_text("[]", encoding="utf-8")
            (root / "metaharness.json").write_text(
                """
                {
                  "objective": "demo",
                  "constraints": [],
                  "required_files": [],
                  "backend_plugins": {
                    "cursor": {
                      "factory": "custom_plugin:create_backend",
                      "options": {
                        "model": "cursor-pro"
                      }
                    }
                  }
                }
                """.strip(),
                encoding="utf-8",
            )

            project = load_coding_tool_project(root)
            self.assertIn("cursor", project.backend_plugins)
            self.assertEqual("custom_plugin:create_backend", project.backend_plugins["cursor"].factory)
            self.assertEqual("cursor-pro", project.backend_plugins["cursor"].options["model"])

    def test_make_backend_supports_plugin_factory(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "baseline").mkdir()
            (root / "tasks.json").write_text("[]", encoding="utf-8")
            (root / "custom_plugin.py").write_text(
                """
from metaharness.proposer.fake import FakeBackend

def create_backend(project, options):
    marker = str(options.get("marker", "default"))
    return FakeBackend(
        mutation=lambda request: {
            "relative_path": "PLUGIN.md",
            "content": marker + "\\n",
            "summary": f"plugin:{marker}",
            "final_text": f"plugin final {marker}",
        }
    )
                """.strip(),
                encoding="utf-8",
            )
            (root / "metaharness.json").write_text(
                """
                {
                  "objective": "demo",
                  "constraints": [],
                  "required_files": [],
                  "backend_plugins": {
                    "cursor": {
                      "factory": "custom_plugin:create_backend",
                      "options": {
                        "marker": "from-plugin"
                      }
                    }
                  },
                  "backends": {
                    "cursor": {
                      "marker": "from-backend-config"
                    }
                  }
                }
                """.strip(),
                encoding="utf-8",
            )

            project = load_coding_tool_project(root)
            sys.path.insert(0, str(root))
            try:
                merged = resolve_backend_options("cursor", project, overrides={"marker": "from-override"})
                self.assertEqual("from-override", merged["marker"])
                backend = make_backend("cursor", project, overrides={"marker": "from-override"})
                self.assertIsInstance(backend, FakeBackend)
            finally:
                sys.path.remove(str(root))
                sys.modules.pop("custom_plugin", None)

    def test_resolve_command_shell_falls_back_when_zsh_is_unavailable(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            with patch("shutil.which") as which:
                which.side_effect = lambda name: {
                    "bash": "/usr/bin/bash",
                    "zsh": None,
                    "sh": "/usr/bin/sh",
                }.get(name)
                self.assertEqual("/usr/bin/bash", _resolve_command_shell())


if __name__ == "__main__":
    unittest.main()
