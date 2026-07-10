"""TDD-тесты реального алгоритма минимизации ДКА."""

from collections.abc import Mapping
from math import isnan

from dfa_app.algorithms.pt_dfa_minimizer import PTDFAMinimizer
from dfa_app.domain.models import DFA, TransitionKey
from dfa_app.domain.validation import validate_dfa


def assert_minimized_dfa(
    actual: DFA,
    *,
    alphabet: tuple[str, ...],
    state_count: int,
    transitions: Mapping[TransitionKey, str],
    initial_state: str,
    final_states: frozenset[str],
) -> None:
    """Проверяет все значимые части автомата после минимизации."""

    # Алгоритм минимизации не должен изменять алфавит.
    assert actual.alphabet == alphabet
    # Состав состояний определяется ключами и значениями переходов,
    # поэтому отдельно достаточно проверить их итоговое количество.
    assert actual.size == state_count
    assert dict(actual.transitions) == dict(transitions)
    assert actual.initial_state == initial_state
    assert actual.final_states == final_states


def dfa_with_equivalent_final_states() -> DFA:
    """ДКА, в котором конечные q1 и q2 эквивалентны."""

    return DFA(
        states=("q0", "q1", "q2"),
        alphabet=("0", "1"),
        transitions={
            ("q0", "0"): "q1",
            ("q0", "1"): "q2",
            ("q1", "0"): "q1",
            ("q1", "1"): "q2",
            ("q2", "0"): "q1",
            ("q2", "1"): "q2",
        },
        initial_state="q0",
        final_states=frozenset({"q1", "q2"}),
    )


def partial_dfa_with_equivalent_final_states() -> DFA:
    """PT-DFA, в котором часть переходов не задана."""

    return DFA(
        states=("q0", "q1", "q2"),
        alphabet=("0", "1"),
        transitions={
            ("q0", "0"): "q1",
            ("q0", "1"): "q2",
            ("q1", "0"): "q1",
            ("q2", "0"): "q2",
        },
        initial_state="q0",
        final_states=frozenset({"q1", "q2"}),
    )


def distinguishable_dfa() -> DFA:
    """ДКА с различимыми конечным и неконечным состояниями."""

    return DFA(
        states=("q0", "q1"),
        alphabet=("0", "1"),
        transitions={
            ("q0", "0"): "q0",
            ("q0", "1"): "q1",
            ("q1", "0"): "q0",
            ("q1", "1"): "q1",
        },
        initial_state="q0",
        final_states=frozenset({"q1"}),
    )


def dfa_with_unreachable_state() -> DFA:
    """ДКА с недостижимым состоянием dead."""

    return DFA(
        states=("q0", "q1", "dead"),
        alphabet=("0",),
        transitions={
            ("q0", "0"): "q1",
            ("q1", "0"): "q1",
            ("dead", "0"): "dead",
        },
        initial_state="q0",
        final_states=frozenset({"q1"}),
    )


def equivalent_dfa(*, all_final: bool) -> DFA:
    """ДКА, в котором все достижимые состояния эквивалентны."""

    return DFA(
        states=("q0", "q1"),
        alphabet=("0",),
        transitions={
            ("q0", "0"): "q1",
            ("q1", "0"): "q0",
        },
        initial_state="q0",
        final_states=frozenset({"q0", "q1"}) if all_final else frozenset(),
    )


def already_minimal_dfa() -> DFA:
    """Минимальный трёхсостояний ДКА для подсчёта длины слова по модулю три."""

    return DFA(
        states=("q0", "q1", "q2"),
        alphabet=("a",),
        transitions={
            ("q0", "a"): "q1",
            ("q1", "a"): "q2",
            ("q2", "a"): "q0",
        },
        initial_state="q0",
        final_states=frozenset({"q0"}),
    )


def test_merges_equivalent_final_states() -> None:
    """Эквивалентные конечные состояния должны образовать один блок."""

    minimized = PTDFAMinimizer().minimize(dfa_with_equivalent_final_states())

    assert_minimized_dfa(
        minimized,
        alphabet=("0", "1"),
        state_count=2,
        transitions={
            ("{q0}", "0"): "{q1,q2}",
            ("{q0}", "1"): "{q1,q2}",
            ("{q1,q2}", "0"): "{q1,q2}",
            ("{q1,q2}", "1"): "{q1,q2}",
        },
        initial_state="{q0}",
        final_states=frozenset({"{q1,q2}"}),
    )


def test_minimizes_partial_transition_function() -> None:
    """Отсутствующие переходы PT-DFA не должны достраиваться фиктивным состоянием."""

    minimized = PTDFAMinimizer().minimize(partial_dfa_with_equivalent_final_states())

    assert_minimized_dfa(
        minimized,
        alphabet=("0", "1"),
        state_count=2,
        transitions={
            ("{q0}", "0"): "{q1,q2}",
            ("{q0}", "1"): "{q1,q2}",
            ("{q1,q2}", "0"): "{q1,q2}",
        },
        initial_state="{q0}",
        final_states=frozenset({"{q1,q2}"}),
    )


def test_keeps_distinguishable_states_separate() -> None:
    """Конечное и неконечное состояния нельзя объединять."""

    minimized = PTDFAMinimizer().minimize(distinguishable_dfa())

    assert_minimized_dfa(
        minimized,
        alphabet=("0", "1"),
        state_count=2,
        transitions={
            ("{q0}", "0"): "{q0}",
            ("{q0}", "1"): "{q1}",
            ("{q1}", "0"): "{q0}",
            ("{q1}", "1"): "{q1}",
        },
        initial_state="{q0}",
        final_states=frozenset({"{q1}"}),
    )


def test_removes_unreachable_state_before_minimization() -> None:
    """Недостижимое состояние не должно попадать в минимальный ДКА."""

    minimized = PTDFAMinimizer().minimize(dfa_with_unreachable_state())

    assert_minimized_dfa(
        minimized,
        alphabet=("0",),
        state_count=2,
        transitions={
            ("{q0}", "0"): "{q1}",
            ("{q1}", "0"): "{q1}",
        },
        initial_state="{q0}",
        final_states=frozenset({"{q1}"}),
    )


def test_returns_empty_pt_dfa_for_empty_language() -> None:
    """Если финальных состояний нет, алгоритм возвращает минимальный PT-DFA пустого языка."""

    minimized = PTDFAMinimizer().minimize(equivalent_dfa(all_final=False))

    assert_minimized_dfa(
        minimized,
        alphabet=("0",),
        state_count=1,
        transitions={},
        initial_state="{пустой}",
        final_states=frozenset(),
    )


def test_merges_all_equivalent_states() -> None:
    """Все эквивалентные состояния должны схлопнуться в один блок."""

    minimized = PTDFAMinimizer().minimize(equivalent_dfa(all_final=True))

    assert_minimized_dfa(
        minimized,
        alphabet=("0",),
        state_count=1,
        transitions={("{q0,q1}", "0"): "{q0,q1}"},
        initial_state="{q0,q1}",
        final_states=frozenset({"{q0,q1}"}),
    )


def test_preserves_number_of_states_for_already_minimal_dfa() -> None:
    """Уже минимальный автомат должен сохранить три различимых состояния."""

    minimized = PTDFAMinimizer().minimize(already_minimal_dfa())

    assert_minimized_dfa(
        minimized,
        alphabet=("a",),
        state_count=3,
        transitions={
            ("{q0}", "a"): "{q1}",
            ("{q1}", "a"): "{q2}",
            ("{q2}", "a"): "{q0}",
        },
        initial_state="{q0}",
        final_states=frozenset({"{q0}"}),
    )


def test_keeps_generated_block_names_unique() -> None:
    """Разные блоки не должны схлопываться из-за одинакового строкового имени."""

    # Блок из двух состояний {a, b} и блок из одного состояния с именем "a,b"
    # имеют одинаковое естественное отображение "{a,b}". Алгоритм обязан
    # различить их, иначе словарь переходов потеряет часть рёбер.
    dfa = DFA(
        states=("q0", "a", "b", "a,b"),
        alphabet=("0", "1", "2", "x"),
        transitions={
            ("q0", "0"): "a",
            ("q0", "1"): "b",
            ("q0", "2"): "a,b",
            ("a", "x"): "a",
            ("b", "x"): "b",
        },
        initial_state="q0",
        final_states=frozenset({"a", "b", "a,b"}),
    )

    minimized = PTDFAMinimizer().minimize(dfa)

    validate_dfa(minimized)
    assert_minimized_dfa(
        minimized,
        alphabet=("0", "1", "2", "x"),
        state_count=3,
        transitions={
            ("{a,b}", "x"): "{a,b}",
            ("{q0}", "0"): "{a,b}",
            ("{q0}", "1"): "{a,b}",
            ("{q0}", "2"): "{a,b}#2",
        },
        initial_state="{q0}",
        final_states=frozenset({"{a,b}", "{a,b}#2"}),
    )


def test_metadata_contains_callable_bounds() -> None:
    """Численные границы метаданных должны соблюдать контракт AlgorithmMetadata."""

    metadata = PTDFAMinimizer().metadata

    assert callable(metadata.upper_bound)
    assert callable(metadata.lower_bound)
    assert metadata.upper_bound(8, 3) > 0
    assert isnan(metadata.lower_bound(8, 3))
