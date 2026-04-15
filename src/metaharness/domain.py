from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .core.protocols import EvaluatorProtocol, ValidatorProtocol
from .models import EvaluationResult, ValidationResult


class DomainAdapterProtocol(Protocol):
    def validate(self, workspace: Path) -> ValidationResult: ...

    def evaluate_search(self, workspace: Path) -> EvaluationResult: ...

    def evaluate_test(self, workspace: Path) -> EvaluationResult | None: ...


@dataclass(slots=True)
class LegacyDomainAdapter:
    """Compatibility adapter that wraps existing validator/evaluator pairs."""

    validator: ValidatorProtocol
    evaluator: EvaluatorProtocol

    def validate(self, workspace: Path) -> ValidationResult:
        return self.validator.validate(workspace)

    def evaluate_search(self, workspace: Path) -> EvaluationResult:
        return self.evaluator.evaluate(workspace)

    def evaluate_test(self, workspace: Path) -> EvaluationResult | None:
        # Legacy integrations had a single evaluation stage only.
        return None
