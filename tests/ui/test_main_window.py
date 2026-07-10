from pathlib import Path

from dfa_app.algorithms.pt_dfa_minimizer import PTDFAMinimizer
from dfa_app.algorithms.base import MinimizationResult
from dfa_app.domain.models import DFA
from dfa_app.services.processing import DFAProcessingService, ProcessedDFA
from dfa_app.ui.automata_graph import AutomataGraphView
from dfa_app.ui.main_window import MainWindow


def input_file(tmp_path: Path) -> Path:
    path = tmp_path / "input.csv"
    path.write_text(
        "states;alphabet;transitions;initial;finals\n"
        "q0|q1;0;q0,0->q1|q1,0->q1;q0;q1\n"
        "a|b|c;x;a,x->b|b,x->c|c,x->c;a;c\n"
        "bad;0;bad,0->missing;bad;bad\n",
        encoding="utf-8",
    )
    return path


def cycle_dfa(state_count: int) -> DFA:
    """Связный большой DFA с одним переходом из каждого состояния."""

    states = tuple(f"q{index}" for index in range(state_count))
    return DFA(
        states=states,
        alphabet=("a",),
        transitions={
            (state, "a"): states[(index + 1) % state_count]
            for index, state in enumerate(states)
        },
        initial_state=states[0],
        final_states=frozenset({states[0]}),
    )


def processed(dfa: DFA) -> ProcessedDFA:
    return ProcessedDFA(
        dfa,
        MinimizationResult(
            dfa=dfa,
            classes={state: frozenset({state}) for state in dfa.states},
            discarded_states=frozenset(),
        ),
    )


def test_window_loads_results_errors_and_automata_graphs(qtbot, tmp_path: Path):
    window = MainWindow(DFAProcessingService(PTDFAMinimizer()))
    qtbot.addWidget(window)
    window.show()

    window.load_file(str(input_file(tmp_path)))

    assert window.file_label.text() == "input.csv"
    assert window.results_table.rowCount() == 2
    assert window.results_table.item(0, 1).text() == "2"
    assert window.error_list.count() == 1
    assert window.chart.objectName() == "automataGraphView"
    assert len(window.chart.figure.axes) == 2
    assert window.chart.figure.axes[0].get_title() == "Исходный автомат · 2 сост."
    assert window.chart.figure.axes[1].get_title() == "Минимизированный · 2 сост."
    # На каждой панели есть окружности состояний и стрелки переходов.
    assert len(window.chart.figure.axes[0].patches) > 2
    assert len(window.chart.figure.axes[1].patches) > 2


def test_window_switches_graphs_with_selected_result_row(qtbot, tmp_path: Path):
    window = MainWindow(DFAProcessingService(PTDFAMinimizer()))
    qtbot.addWidget(window)
    window.show()
    window.load_file(str(input_file(tmp_path)))

    window.results_table.selectRow(1)

    assert window.chart.figure.axes[0].get_title() == "Исходный автомат · 3 сост."
    assert window.chart.figure.axes[1].get_title() == "Минимизированный · 3 сост."


def test_window_clears_previous_results_when_file_has_no_valid_rows(qtbot, tmp_path: Path):
    window = MainWindow(DFAProcessingService(PTDFAMinimizer()))
    qtbot.addWidget(window)
    window.load_file(str(input_file(tmp_path)))
    empty = tmp_path / "empty.csv"
    empty.write_text("", encoding="utf-8")

    window.load_file(str(empty))

    assert window.results_table.rowCount() == 0
    assert window.error_list.count() == 1
    assert len(window.chart.figure.axes) == 2
    assert window.chart.figure.axes[0].texts[0].get_text() == "Загрузите файл с автоматами"


def test_edge_label_chooses_position_away_from_node_and_line(qtbot):
    """Подпись должна отказаться от кандидата поверх состояния и перехода."""

    view = AutomataGraphView()
    qtbot.addWidget(view)
    view.figure.clear()
    axes = view.figure.subplots()
    occupied = [(-0.2, -0.2, 0.2, 0.2)]
    horizontal_edge = ((-1.0, 0.0), (1.0, 0.0))

    view._place_label(
        axes,
        "a",
        ((0.0, 0.0), (0.0, 0.4)),
        occupied,
        [horizontal_edge],
    )

    assert axes.texts[-1].get_position() == (0.0, 0.4)


def test_loop_is_directed_outward_from_graph_center(qtbot):
    """Середина петли верхнего узла должна находиться снаружи раскладки."""

    view = AutomataGraphView()
    qtbot.addWidget(view)
    view.figure.clear()
    axes = view.figure.subplots()

    loop_path = view._draw_loop(
        axes,
        (0.0, 0.95),
        0.16,
        "#2563eb",
        avoid_left=False,
    )

    assert loop_path[len(loop_path) // 2][1] > 0.95 + 0.16


def test_automaton_over_fifteen_states_shows_summary(qtbot):
    """Граф больше 15 состояний заменяется читаемой сводкой."""

    dfa = cycle_dfa(16)
    view = AutomataGraphView()
    qtbot.addWidget(view)

    view.show_comparison(processed(dfa))

    assert not view.figure.axes[0].patches
    assert any(
        "больше 15" in text.get_text()
        for text in view.figure.axes[0].texts
    )


def test_fifteen_states_are_still_drawn_as_graph(qtbot):
    """Ровно 15 состояний входят в разрешённую границу отображения."""

    dfa = cycle_dfa(15)
    view = AutomataGraphView()
    qtbot.addWidget(view)

    view.show_comparison(processed(dfa))

    assert len(view.figure.axes[0].patches) >= dfa.size
    assert not any("больше 15" in text.get_text() for text in view.figure.axes[0].texts)


def test_large_automaton_shows_summary_instead_of_graph(qtbot):
    """Тысячи состояний не должны создавать тысячи объектов Matplotlib."""

    dfa = cycle_dfa(2_000)
    view = AutomataGraphView()
    qtbot.addWidget(view)

    view.show_comparison(processed(dfa))

    for axes in view.figure.axes[:2]:
        assert not axes.patches
        assert any(
            "больше 15" in text.get_text()
            for text in axes.texts
        )


def test_graph_panel_titles_have_same_vertical_position(qtbot):
    """Заголовки двух графов находятся на одной линии."""

    dfa = cycle_dfa(5)
    view = AutomataGraphView()
    qtbot.addWidget(view)
    view.show_comparison(processed(dfa))
    view.draw()

    panel_titles = view.figure.texts[-2:]
    assert len(panel_titles) == 2
    assert len({title.get_position()[1] for title in panel_titles}) == 1


def test_window_populates_transition_and_class_tabs(qtbot, tmp_path: Path):
    window = MainWindow(DFAProcessingService(PTDFAMinimizer()))
    qtbot.addWidget(window)
    window.load_file(str(input_file(tmp_path)))

    assert window.detail_tabs.count() == 3
    assert [window.detail_tabs.tabText(i) for i in range(3)] == [
        "Графы", "Переходы", "Классы"
    ]
    assert window.transitions_table.rowCount() == 2
    assert window.transitions_table.item(0, 0).text().startswith("C")
    assert "Начальное состояние: C0" in window.transition_info.text()
    assert window.classes_table.rowCount() == 2
    assert window.classes_table.item(0, 0).text() == "C0"
    assert window.save_button.isEnabled()


def test_save_button_exports_selected_result(qtbot, tmp_path: Path, monkeypatch):
    window = MainWindow(DFAProcessingService(PTDFAMinimizer()))
    qtbot.addWidget(window)
    window.load_file(str(input_file(tmp_path)))
    destination = tmp_path / "selected.csv"
    monkeypatch.setattr(
        "dfa_app.ui.main_window.QFileDialog.getSaveFileName",
        lambda *_args, **_kwargs: (str(destination), "CSV (*.csv)"),
    )

    window.save_button.click()

    assert destination.exists()
    assert (tmp_path / "selected.classes.csv").exists()
