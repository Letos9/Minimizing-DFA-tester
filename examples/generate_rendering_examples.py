r"""Генерирует DFA для проверки трёх режимов визуализации интерфейса.

Запуск из корня проекта:

    .venv\Scripts\python examples\generate_rendering_examples.py

Результат записывается рядом со скриптом в ``automata_rendering_modes.csv``.
Все автоматы связны: переход по первому символу образует цикл через состояния.
"""

from __future__ import annotations

import csv
from pathlib import Path

HEADERS = ("states", "alphabet", "transitions", "initial", "finals")
OUTPUT_PATH = Path(__file__).with_name("automata_rendering_modes.csv")


def make_automaton_row(
    *,
    prefix: str,
    state_count: int,
    alphabet_size: int,
    final_step: int,
) -> dict[str, str]:
    """Создаёт полный связный DFA с детерминированными переходами."""

    states = tuple(f"{prefix}{index}" for index in range(state_count))
    alphabet = tuple(f"a{index}" for index in range(alphabet_size))
    transitions: list[str] = []

    for state_index, state in enumerate(states):
        for symbol_index, symbol in enumerate(alphabet):
            # a0 задаёт цикл +1 и гарантирует достижимость. Остальные шаги
            # различаются, создавая насыщенный, но воспроизводимый граф.
            step = 1 if symbol_index == 0 else 2 * symbol_index + 1
            target = states[(state_index + step) % state_count]
            transitions.append(f"{state},{symbol}->{target}")

    final_states = states[::final_step]
    return {
        "states": "|".join(states),
        "alphabet": "|".join(alphabet),
        "transitions": "|".join(transitions),
        "initial": states[0],
        "finals": "|".join(final_states),
    }


def main() -> None:
    rows = (
        # 12 состояний, 36 переходов: полный режим с подписями.
        make_automaton_row(
            prefix="detail_",
            state_count=12,
            alphabet_size=3,
            final_step=4,
        ),
        # Ровно 15 состояний — верхняя граница отображения графа.
        make_automaton_row(
            prefix="detail_boundary_",
            state_count=15,
            alphabet_size=3,
            final_step=5,
        ),
        # 16 состояний — первый размер, для которого граф заменяется сводкой.
        make_automaton_row(
            prefix="after_detail_",
            state_count=16,
            alphabet_size=2,
            final_step=4,
        ),
        # 80 состояний, 240 переходов: упрощённый режим без подписей рёбер.
        make_automaton_row(
            prefix="medium_",
            state_count=80,
            alphabet_size=3,
            final_step=11,
        ),
        # 150 состояний: сводка включается по ограничению числа состояний.
        make_automaton_row(
            prefix="states_limit_",
            state_count=150,
            alphabet_size=2,
            final_step=17,
        ),
    )

    with OUTPUT_PATH.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=HEADERS, delimiter=";")
        writer.writeheader()
        writer.writerows(rows)

    print(f"Создан файл: {OUTPUT_PATH}")
    for index, row in enumerate(rows, start=1):
        state_count = len(row["states"].split("|"))
        transition_count = len(row["transitions"].split("|"))
        print(f"{index}: n={state_count}, m={transition_count}")


if __name__ == "__main__":
    main()
