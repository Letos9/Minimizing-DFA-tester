from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from types import MappingProxyType
from typing import Callable, Mapping

from dfa_app.domain.models import DFA

ComplexityFunction = Callable[[int, int], float]


@dataclass(frozen=True, slots=True)
class AlgorithmMetadata:
    name: str
    upper_label: str
    lower_label: str
    upper_bound: ComplexityFunction
    lower_bound: ComplexityFunction


@dataclass(frozen=True, slots=True)
class MinimizationResult:
    """Самостоятельный минимальный ДКА и сведения о происхождении состояний."""

    dfa: DFA
    classes: Mapping[str, frozenset[str]]
    discarded_states: frozenset[str]

    def __post_init__(self) -> None:
        normalized = {
            state: frozenset(members)
            for state, members in self.classes.items()
        }
        object.__setattr__(self, "classes", MappingProxyType(normalized))
        object.__setattr__(self, "discarded_states", frozenset(self.discarded_states))


class DFAMinimizer(ABC):
    @property
    @abstractmethod
    def metadata(self) -> AlgorithmMetadata:
        raise NotImplementedError

    @abstractmethod
    def minimize(self, dfa: DFA) -> MinimizationResult:
        raise NotImplementedError
