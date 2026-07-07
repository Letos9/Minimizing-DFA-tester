from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from dfa_app.algorithms.base import AlgorithmMetadata, DFAMinimizer
from dfa_app.domain.models import DFA
from dfa_app.domain.validation import validate_dfa
from dfa_app.importers.file_loader import RowError, load_automata


@dataclass(frozen=True, slots=True)
class ProcessedDFA:
    source: DFA
    minimized: DFA


@dataclass(frozen=True, slots=True)
class ProcessingResult:
    items: tuple[ProcessedDFA, ...]
    errors: tuple[RowError, ...]
    metadata: AlgorithmMetadata


class DFAProcessingService:
    def __init__(self, minimizer: DFAMinimizer) -> None:
        self.minimizer = minimizer

    def process_file(self, file_path: str | Path) -> ProcessingResult:
        loaded = load_automata(file_path)
        items: list[ProcessedDFA] = []
        errors = list(loaded.errors)
        for index, dfa in enumerate(loaded.automata, start=1):
            try:
                minimized = self.minimizer.minimize(dfa)
                validate_dfa(minimized)
                items.append(ProcessedDFA(dfa, minimized))
            except Exception as exc:
                errors.append(RowError(index + 1, f"ошибка алгоритма: {exc}"))
        return ProcessingResult(tuple(items), tuple(errors), self.minimizer.metadata)

