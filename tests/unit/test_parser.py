import pytest

from dfa_app.importers.parser import RowParseError, parse_row


VALID_ROW = {
    "states": "q0|q1",
    "alphabet": "0|1",
    "transitions": "q0,0->q0|q0,1->q1|q1,0->q0|q1,1->q1",
    "initial": "q0",
    "finals": "q1",
}


def test_parse_row_builds_dfa():
    dfa = parse_row(VALID_ROW)

    assert dfa.size == 2
    assert dfa.transitions[("q0", "1")] == "q1"


def test_duplicate_transition_is_rejected():
    row = dict(VALID_ROW)
    row["transitions"] += "|q0,0->q1"

    with pytest.raises(RowParseError, match="более одного раза"):
        parse_row(row)


def test_bad_transition_syntax_is_rejected():
    row = dict(VALID_ROW)
    row["transitions"] = "q0-0-q1"

    with pytest.raises(RowParseError, match="ожидается"):
        parse_row(row)

