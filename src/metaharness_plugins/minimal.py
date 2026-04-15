"""Minimal example plugin backend for metaharness."""

from pathlib import Path

from metaharness.models import AgentEvent, ProposalResult


class MinimalPluginBackend:
    """Minimal backend plugin demonstrating the factory contract."""

    def __init__(self, *, project, options, backend_name):
        self.name = backend_name
        self.project = project
        self.options = options

    def prepare(self, request):
        return {
            "prompt": f"Minimal plugin: {request.instructions.objective}",
            "model": self.options.get("model", "default"),
        }

    def invoke(self, prepared):
        return ProposalExecution(
            stdout_path=None,
            stderr_path=None,
            returncode=0,
            metadata={"prompt": prepared["prompt"]},
        )

    def collect(self, execution):
        prompt = execution.metadata.get("prompt", "")
        return ProposalResult(
            applied=True,
            summary="Minimal plugin completed",
            final_text=prompt,
            changed_files=[],
            events=[
                AgentEvent(
                    ts=None,
                    kind="message",
                    text=prompt,
                )
            ],
            metadata={"model": self.options.get("model", "default")},
        )


class ProposalExecution:
    def __init__(self, stdout_path, stderr_path, returncode, metadata):
        self.stdout_path = stdout_path
        self.stderr_path = stderr_path
        self.returncode = returncode
        self.metadata = metadata


def create_backend(**kwargs):
    """Factory function for the minimal plugin."""
    return MinimalPluginBackend(
        project=kwargs.get("project"),
        options=kwargs.get("options", {}),
        backend_name=kwargs.get("backend_name", "minimal"),
    )