from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

TransitionKey = tuple[str, str]


@dataclass(frozen=True, slots=True)
class DFA:
    states: tuple[str, ...]
    alphabet: tuple[str, ...]
    transitions: Mapping[TransitionKey, str]
    initial_state: str
    final_states: frozenset[str]

    def __post_init__(self) -> None:
        object.__setattr__(self, "states", tuple(self.states))
        object.__setattr__(self, "alphabet", tuple(self.alphabet))
        object.__setattr__(self, "transitions", MappingProxyType(dict(self.transitions)))
        object.__setattr__(self, "final_states", frozenset(self.final_states))

    @property
    def size(self) -> int:
        return len(self.states)

