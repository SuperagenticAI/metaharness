"""Pretend host (Omnigent / UHP / AgentSky-style) that embeds optimize_harness."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from metaharness import EvaluationResult, FakeBackend, ValidationResult, optimize_harness

EXAMPLE_DIR = Path(__file__).resolve().parent
BASELINE_DIR = EXAMPLE_DIR / "workspace"


class HostValidator:
    def validate(self, workspace: Path) -> ValidationResult:
        path = workspace / "agent.md"
        if not path.exists() or not path.read_text(encoding="utf-8").strip():
            return ValidationResult(ok=False, summary="agent.md is missing")
        return ValidationResult(ok=True, summary="host agent files are present")


class HostEvaluator:
    def evaluate(self, workspace: Path) -> EvaluationResult:
        text = (workspace / "agent.md").read_text(encoding="utf-8")
        score = 1.0 if "Never use destructive git commands" in text else 0.25
        return EvaluationResult(
            objective=score,
            metrics={"score": score},
            summary="Host-side check for improved agent instructions.",
        )


def make_proposer() -> FakeBackend:
    return FakeBackend(
        mutation=lambda request: {
            "relative_path": "agent.md",
            "content": (
                "# Host Agent\n\n"
                "- Read the repository before editing.\n"
                "- Never use destructive git commands such as `git reset --hard`.\n"
                "- Keep host files file-backed; do not call a proprietary proposer API.\n"
            ),
            "summary": f"Host-embedded proposal for {request.candidate_id}.",
            "final_text": "Improved host agent instructions via optimize_harness.",
        }
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Embed metaharness from a host runtime.")
    parser.add_argument("--run-dir", default=str(EXAMPLE_DIR / "runs" / "embed-host"))
    parser.add_argument("--budget", type=int, default=1)
    args = parser.parse_args(argv)

    result = optimize_harness(
        baseline=BASELINE_DIR,
        proposer=make_proposer(),
        evaluator=HostEvaluator(),
        validator=HostValidator(),
        run_dir=Path(args.run_dir),
        budget=args.budget,
        objective="Improve host agent files via the metaharness kernel.",
        constraints=[
            "Keep the host workspace file-backed.",
            "Do not wrap AgentSky or HarnessRouter as a proposer backend.",
        ],
    )
    print(f"best_candidate_id={result.best_candidate_id}")
    print(f"best_objective={result.best_objective:.3f}")
    print(f"run_dir={result.run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
