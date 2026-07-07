from pathlib import Path

from dfa_app.algorithms.minimizer import PassthroughMinimizer
from dfa_app.services.processing import DFAProcessingService
from dfa_app.ui.main_window import MainWindow


def input_file(tmp_path: Path) -> Path:
    path = tmp_path / "input.csv"
    path.write_text(
        "states;alphabet;transitions;initial;finals\n"
        "q0|q1;0;q0,0->q1|q1,0->q1;q0;q1\n"
        "bad;0;;bad;bad\n",
        encoding="utf-8",
    )
    return path


def test_window_loads_results_errors_and_chart(qtbot, tmp_path: Path):
    window = MainWindow(DFAProcessingService(PassthroughMinimizer()))
    qtbot.addWidget(window)
    window.show()

    window.load_file(str(input_file(tmp_path)))

    assert window.file_label.text() == "input.csv"
    assert window.results_table.rowCount() == 1
    assert window.results_table.item(0, 1).text() == "2"
    assert window.error_list.count() == 1
    assert len(window.chart.figure.axes) == 1


def test_window_clears_previous_results_when_file_has_no_valid_rows(qtbot, tmp_path: Path):
    window = MainWindow(DFAProcessingService(PassthroughMinimizer()))
    qtbot.addWidget(window)
    window.load_file(str(input_file(tmp_path)))
    empty = tmp_path / "empty.csv"
    empty.write_text("", encoding="utf-8")

    window.load_file(str(empty))

    assert window.results_table.rowCount() == 0
    assert window.error_list.count() == 1
