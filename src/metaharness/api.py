from pathlib import Path
from typing import Sequence

from .core.engine import MetaHarnessEngine
from .core.protocols import EvaluatorProtocol, ValidatorProtocol
from .domain import DomainAdapterProtocol, LegacyDomainAdapter
from .models import OptimizeResult
from .proposer.base import ProposerBackend


class NoOpValidator:
    def validate(self, workspace: Path):  # pragma: no cover - trivial
        from .models import ValidationResult

        return ValidationResult(ok=True, summary="No validator configured.")


def optimize_harness(
    baseline: str | Path,
    proposer: ProposerBackend,
    evaluator: EvaluatorProtocol | None,
    run_dir: str | Path,
    budget: int,
    objective: str,
    validator: ValidatorProtocol | None = None,
    domain_adapter: DomainAdapterProtocol | None = None,
    constraints: Sequence[str] | None = None,
    allowed_write_paths: Sequence[str] | None = None,
    trace_evidence_path: str | Path | None = None,
    search_mode: str = "hill-climb",
    proposal_batch_size: int = 1,
    selection_policy: str = "single",
) -> OptimizeResult:
    if domain_adapter is None:
        if evaluator is None:
            raise ValueError("either evaluator or domain_adapter must be provided")
        resolved_validator = validator or NoOpValidator()
        domain_adapter = LegacyDomainAdapter(validator=resolved_validator, evaluator=evaluator)

    engine = MetaHarnessEngine(
        baseline=Path(baseline),
        proposer=proposer,
        domain_adapter=domain_adapter,
        run_dir=Path(run_dir),
        budget=budget,
        objective=objective,
        constraints=list(constraints or []),
        allowed_write_paths=list(allowed_write_paths or []),
        trace_evidence_path=Path(trace_evidence_path) if trace_evidence_path is not None else None,
        search_mode=search_mode,
        proposal_batch_size=proposal_batch_size,
        selection_policy=selection_policy,
    )
    return engine.run()
