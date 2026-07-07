from __future__ import annotations

from collections.abc import Mapping

from dfa_app.domain.models import DFA
from dfa_app.domain.validation import validate_dfa

EXPECTED_HEADERS = ("states", "alphabet", "transitions", "initial", "finals")


class RowParseError(ValueError):
    pass


def _split(value: object, field: str, *, allow_empty: bool = False) -> tuple[str, ...]:
    text = "" if value is None else str(value).strip()
    if not text:
        return () if allow_empty else ()
    items = tuple(part.strip() for part in text.split("|") if part.strip())
    if not items and not allow_empty:
        raise RowParseError(f"поле {field} пусто")
    return items


def parse_row(row: Mapping[str, object]) -> DFA:
    missing_headers = [name for name in EXPECTED_HEADERS if name not in row]
    if missing_headers:
        raise RowParseError(f"отсутствуют колонки: {', '.join(missing_headers)}")

    states = _split(row["states"], "states")
    alphabet = _split(row["alphabet"], "alphabet")
    initial = "" if row["initial"] is None else str(row["initial"]).strip()
    finals = frozenset(_split(row["finals"], "finals", allow_empty=True))
    transitions: dict[tuple[str, str], str] = {}

    for item in _split(row["transitions"], "transitions"):
        try:
            left, target = item.split("->", 1)
            source, symbol = left.split(",", 1)
        except ValueError as exc:
            raise RowParseError(f"неверный переход '{item}', ожидается q0,a->q1") from exc
        key = (source.strip(), symbol.strip())
        target = target.strip()
        if not all((*key, target)):
            raise RowParseError(f"переход '{item}' содержит пустое значение")
        if key in transitions:
            raise RowParseError(f"переход ({key[0]}, {key[1]}) задан более одного раза")
        transitions[key] = target

    dfa = DFA(states, alphabet, transitions, initial, finals)
    validate_dfa(dfa)
    return dfa

