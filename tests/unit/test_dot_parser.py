import pytest

from dfa_app.importers.dot_parser import DotParseError, parse_dot


TOY_DFA = '''digraph g {
__start0 [label="" shape="none"]
s1 [shape="doublecircle" label="s1"]
s2 [shape="circle" label="s2"]
__start0 -> s1
s1 -> s2[label="0"]
s1 -> s1[label="1"]
s2 -> s1[label="0"]
s2 -> s2[label="1"]
}
'''


def test_parse_toy_dfa_dot():
    dfa = parse_dot(TOY_DFA)

    assert dfa.states == ("s1", "s2")
    assert dfa.alphabet == ("0", "1")
    assert dfa.initial_state == "s1"
    assert dfa.final_states == frozenset({"s1"})
    assert dfa.transitions[("s2", "1")] == "s2"


def test_dot_requires_single_initial_state():
    source = TOY_DFA.replace("__start0 -> s1", "__start0 -> s1\n__start0 -> s2")

    with pytest.raises(DotParseError, match="ровно один"):
        parse_dot(source)


def test_dot_rejects_nondeterministic_transitions():
    source = TOY_DFA.replace('s1 -> s2[label="0"]', 's1 -> s2[label="0"]\ns1 -> s1[label="0"]')

    with pytest.raises(DotParseError, match="более одного раза"):
        parse_dot(source)
