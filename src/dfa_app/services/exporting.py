"""Экспорт независимого минимизированного ДКА и состава его классов."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from dfa_app.algorithms.base import MinimizationResult


def export_minimization(
    result: MinimizationResult,
    destination: str | Path,
) -> tuple[Path, Path]:
    """Сохраняет ДКА в CSV или DOT и возвращает оба созданных пути."""

    path = Path(destination)
    suffix = path.suffix.lower()
    if suffix == ".csv":
        _write_dfa_csv(result, path)
    elif suffix in {".dot", ".gv"}:
        _write_dfa_dot(result, path)
    else:
        raise ValueError("поддерживаются только форматы CSV и DOT")

    classes_path = path.with_name(f"{path.stem}.classes.csv")
    _write_classes_csv(result, classes_path)
    return path, classes_path


def _write_dfa_csv(result: MinimizationResult, path: Path) -> None:
    dfa = result.dfa
    transitions = "|".join(
        f"{source},{symbol}->{target}"
        for (source, symbol), target in sorted(dfa.transitions.items())
    )
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=("states", "alphabet", "transitions", "initial", "finals"),
            delimiter=";",
        )
        writer.writeheader()
        writer.writerow(
            {
                "states": "|".join(dfa.states),
                "alphabet": "|".join(dfa.alphabet),
                "transitions": transitions,
                "initial": dfa.initial_state,
                "finals": "|".join(sorted(dfa.final_states)),
            }
        )


def _write_dfa_dot(result: MinimizationResult, path: Path) -> None:
    dfa = result.dfa
    quote = lambda value: json.dumps(value, ensure_ascii=False)
    # Экспорт остаётся совместимым не только с Graphviz, но и с собственным
    # строгим DOT-импортёром приложения, который читает только узлы и рёбра.
    lines = ["digraph minimized_dfa {", "  __start [shape=none];"]
    for state in dfa.states:
        shape = "doublecircle" if state in dfa.final_states else "circle"
        lines.append(f"  {quote(state)} [shape={shape}];")
    lines.append(f"  __start -> {quote(dfa.initial_state)};")
    for (source, symbol), target in sorted(dfa.transitions.items()):
        lines.append(f"  {quote(source)} -> {quote(target)} [label={quote(symbol)}];")
    lines.append("}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_classes_csv(result: MinimizationResult, path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, delimiter=";")
        writer.writerow(("type", "class", "source_state"))
        for class_name in result.dfa.states:
            for state in sorted(result.classes[class_name]):
                writer.writerow(("class", class_name, state))
        for state in sorted(result.discarded_states):
            writer.writerow(("discarded", "", state))
