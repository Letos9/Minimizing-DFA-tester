from __future__ import annotations

from dfa_app.domain.models import DFA


class DFAValidationError(ValueError):
    def __init__(self, errors: list[str]) -> None:
        self.errors = tuple(errors)
        super().__init__("; ".join(errors))


def validate_dfa(dfa: DFA) -> None:
    errors: list[str] = []
    states = set(dfa.states)
    alphabet = set(dfa.alphabet)

    if not dfa.states:
        errors.append("список состояний пуст")
    if len(states) != len(dfa.states):
        errors.append("состояния должны быть уникальны")
    if not dfa.alphabet:
        errors.append("алфавит пуст")
    if len(alphabet) != len(dfa.alphabet):
        errors.append("символы алфавита должны быть уникальны")
    if dfa.initial_state not in states:
        errors.append("начальное состояние отсутствует в списке состояний")

    unknown_finals = sorted(dfa.final_states - states)
    if unknown_finals:
        errors.append(f"неизвестные конечные состояния: {', '.join(unknown_finals)}")

    for (source, symbol), target in dfa.transitions.items():
        if source not in states:
            errors.append(f"неизвестное исходное состояние перехода: {source}")
        if symbol not in alphabet:
            errors.append(f"неизвестный символ перехода: {symbol}")
        if target not in states:
            errors.append(f"неизвестное целевое состояние перехода: {target}")

    if errors:
        raise DFAValidationError(errors)
