import pytest

from dfa_app.domain.models import DFA
from dfa_app.domain.validation import DFAValidationError, validate_dfa


def valid_dfa() -> DFA:
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


def test_valid_complete_dfa_is_accepted():
    validate_dfa(valid_dfa())


def test_missing_transition_is_rejected():
    dfa = valid_dfa()
    transitions = dict(dfa.transitions)
    del transitions[("q1", "1")]
    invalid = DFA(dfa.states, dfa.alphabet, transitions, dfa.initial_state, dfa.final_states)

    with pytest.raises(DFAValidationError, match="не заданы переходы"):
        validate_dfa(invalid)


def test_unknown_initial_and_final_states_are_rejected():
    dfa = valid_dfa()
    invalid = DFA(dfa.states, dfa.alphabet, dfa.transitions, "missing", {"other"})

    with pytest.raises(DFAValidationError) as error:
        validate_dfa(invalid)

    assert "начальное состояние" in str(error.value)
    assert "неизвестные конечные" in str(error.value)

