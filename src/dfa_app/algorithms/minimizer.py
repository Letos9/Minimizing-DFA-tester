from __future__ import annotations

from dfa_app.algorithms.base import AlgorithmMetadata, DFAMinimizer
from dfa_app.domain.models import DFA


class PassthroughMinimizer(DFAMinimizer):
    """Replace this class with the project-specific minimization algorithm."""

    @property
    def metadata(self) -> AlgorithmMetadata:
        return AlgorithmMetadata(
            name="Подключаемый алгоритм (заглушка)",
            upper_label="O(n²·|Σ|)",
            lower_label="Ω(n·|Σ|)",
            upper_bound=lambda n, alphabet: float(n * n * alphabet),
            lower_bound=lambda n, alphabet: float(n * alphabet),
        )

    def minimize(self, dfa: DFA) -> DFA:
        return dfa

