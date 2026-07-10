from pathlib import Path

from openpyxl import Workbook

from dfa_app.importers.file_loader import load_automata


HEADER = "states;alphabet;transitions;initial;finals\n"
VALID = "q0|q1;0|1;q0,0->q0|q0,1->q1|q1,0->q0|q1,1->q1;q0;q1\n"
DOT = '''digraph g {
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


def test_load_csv_skips_invalid_rows(tmp_path: Path):
    path = tmp_path / "automata.csv"
    path.write_text(HEADER + VALID + "q0;0;q0,0->missing;q0;q0\n", encoding="utf-8")

    loaded = load_automata(path)

    assert len(loaded.automata) == 1
    assert len(loaded.errors) == 1
    assert loaded.errors[0].row_number == 3


def test_load_txt_supports_utf8_bom(tmp_path: Path):
    path = tmp_path / "automata.txt"
    path.write_text(HEADER + VALID, encoding="utf-8-sig")

    assert len(load_automata(path).automata) == 1


def test_empty_file_returns_error(tmp_path: Path):
    path = tmp_path / "empty.csv"
    path.write_text("", encoding="utf-8")

    loaded = load_automata(path)

    assert not loaded.automata
    assert "пуст" in loaded.errors[0].message


def test_wrong_headers_return_error(tmp_path: Path):
    path = tmp_path / "wrong.csv"
    path.write_text("state;symbols\nq0;0\n", encoding="utf-8")

    loaded = load_automata(path)

    assert "неверные заголовки" in loaded.errors[0].message


def test_load_xlsx(tmp_path: Path):
    path = tmp_path / "automata.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["states", "alphabet", "transitions", "initial", "finals"])
    sheet.append(["q0|q1", "0|1", "q0,0->q0|q0,1->q1|q1,0->q0|q1,1->q1", "q0", "q1"])
    workbook.save(path)

    loaded = load_automata(path)

    assert len(loaded.automata) == 1
    assert not loaded.errors


def test_load_dot(tmp_path: Path):
    path = tmp_path / "ToyDFA.dot"
    path.write_text(DOT, encoding="utf-8")

    loaded = load_automata(path)

    assert not loaded.errors
    assert len(loaded.automata) == 1
    assert loaded.automata[0].initial_state == "s1"
    assert loaded.automata[0].final_states == frozenset({"s1"})


def test_unsupported_extension_returns_error(tmp_path: Path):
    path = tmp_path / "automata.json"
    path.write_text("{}", encoding="utf-8")

    assert "неподдерживаемый" in load_automata(path).errors[0].message
