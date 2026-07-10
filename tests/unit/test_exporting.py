from dfa_app.algorithms.pt_dfa_minimizer import PTDFAMinimizer
from dfa_app.domain.models import DFA
from dfa_app.importers.file_loader import load_automata
from dfa_app.services.exporting import export_minimization


def source_dfa() -> DFA:
    return DFA(
        states=("A", "B", "C", "unused"),
        alphabet=("0", "1"),
        transitions={
            ("A", "0"): "B",
            ("A", "1"): "C",
            ("B", "0"): "B",
            ("C", "0"): "C",
            ("unused", "0"): "unused",
        },
        initial_state="A",
        final_states=frozenset({"B", "C"}),
    )


def test_csv_export_can_be_imported_without_changing_dfa(tmp_path):
    result = PTDFAMinimizer().minimize(source_dfa())
    dfa_path, classes_path = export_minimization(result, tmp_path / "result.csv")

    loaded = load_automata(dfa_path)

    assert not loaded.errors
    assert loaded.automata == (result.dfa,)
    classes_text = classes_path.read_text(encoding="utf-8")
    assert "class;C0;A" in classes_text
    assert "discarded;;unused" in classes_text


def test_dot_export_contains_independent_states_and_is_importable(tmp_path):
    result = PTDFAMinimizer().minimize(source_dfa())
    dfa_path, classes_path = export_minimization(result, tmp_path / "result.dot")

    text = dfa_path.read_text(encoding="utf-8")
    loaded = load_automata(dfa_path)

    assert '"C0"' in text
    assert "{A" not in text
    assert not loaded.errors
    assert loaded.automata == (result.dfa,)
    assert classes_path.name == "result.classes.csv"
