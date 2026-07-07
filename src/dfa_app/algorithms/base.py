from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable

from dfa_app.domain.models import DFA

ComplexityFunction = Callable[[int, int], float]


@dataclass(frozen=True, slots=True)
class AlgorithmMetadata:
    name: str
    upper_label: str
    lower_label: str
    upper_bound: ComplexityFunction
    lower_bound: ComplexityFunction


class DFAMinimizer(ABC):
    @property
    @abstractmethod
    def metadata(self) -> AlgorithmMetadata:
        raise NotImplementedError

    @abstractmethod
    def minimize(self, dfa: DFA) -> DFA:
        raise NotImplementedError

