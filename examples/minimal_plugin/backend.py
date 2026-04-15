"""Minimal example plugin backend for metaharness."""

from dataclasses import dataclass
from pathlib import Path


@dataclass
class ExecutionResult:
    stdout: str
    stderr: str
    exit_code: int
    events: list[dict]
    changed_files: list[str]


class MinimalPluginBackend:
    """Minimal backend plugin demonstrating the factory contract."""

    def __init__(self, *, project, options, backend_name):
        self.name = backend_name
        self.project = project
        self.options = options

    def prepare(self, request):
        return {
            "prompt": f"Minimal plugin: {request.task}",
            "model": self.options.get("model", "default"),
        }

    def invoke(self, prepared):
        return ExecutionResult(
            stdout=f"Processed: {prepared['prompt']}",
            stderr="",
            exit_code=0,
            events=[{"type": "message", "content": prepared["prompt"]}],
            changed_files=[],
        )

    def collect(self, execution):
        return {
            "result": {
                "success": execution.exit_code == 0,
                "events": execution.events,
                "changed_files": execution.changed_files,
            }
        }


def create_backend(**kwargs):
    """Factory function for the minimal plugin."""
    return MinimalPluginBackend(
        project=kwargs.get("project"),
        options=kwargs.get("options", {}),
        backend_name=kwargs.get("backend_name", "minimal"),
    )