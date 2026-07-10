from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMainWindow,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from dfa_app.services.processing import DFAProcessingService, ProcessedDFA, ProcessingResult
from dfa_app.services.exporting import export_minimization
from dfa_app.ui.automata_graph import AutomataGraphView


class MainWindow(QMainWindow):
    def __init__(self, service: DFAProcessingService) -> None:
        super().__init__()
        self.service = service
        self._processed_items: tuple[ProcessedDFA, ...] = ()
        self.setFont(QFont("Segoe UI", 10))
        self.setWindowTitle("Минимизация ДКА")
        self.resize(1280, 850)

        self.load_button = QPushButton("Загрузить файл")
        self.load_button.setObjectName("loadFileButton")
        self.file_label = QLabel("Файл не выбран")
        self.file_label.setObjectName("fileNameLabel")
        self.file_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.save_button = QPushButton("Сохранить результат")
        self.save_button.setObjectName("saveResultButton")
        self.save_button.setEnabled(False)
        self.results_table = QTableWidget(0, 4)
        self.results_table.setObjectName("resultsTable")
        self.results_table.setHorizontalHeaderLabels(
            ("№", "Состояний до", "Состояний после", "Алфавит")
        )
        self.results_table.horizontalHeader().setStretchLastSection(True)
        self.results_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.results_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.error_list = QListWidget()
        self.error_list.setObjectName("errorList")
        self.chart = AutomataGraphView()
        self.transition_info = QLabel("Выберите результат")
        self.transition_info.setObjectName("transitionInfoLabel")
        self.transitions_table = QTableWidget(0, 3)
        self.transitions_table.setObjectName("transitionsTable")
        self.transitions_table.setHorizontalHeaderLabels(
            ("Состояние", "Символ", "Следующее состояние")
        )
        self.transitions_table.horizontalHeader().setStretchLastSection(True)
        self.transitions_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.classes_table = QTableWidget(0, 2)
        self.classes_table.setObjectName("classesTable")
        self.classes_table.setHorizontalHeaderLabels(("Класс", "Исходные состояния"))
        self.classes_table.horizontalHeader().setStretchLastSection(True)
        self.classes_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        transition_tab = QWidget()
        transition_layout = QVBoxLayout(transition_tab)
        transition_layout.addWidget(self.transition_info)
        transition_layout.addWidget(self.transitions_table)

        classes_tab = QWidget()
        classes_layout = QVBoxLayout(classes_tab)
        classes_layout.addWidget(self.classes_table)

        self.detail_tabs = QTabWidget()
        self.detail_tabs.setObjectName("detailTabs")
        self.detail_tabs.addTab(self.chart, "Графы")
        self.detail_tabs.addTab(transition_tab, "Переходы")
        self.detail_tabs.addTab(classes_tab, "Классы")

        top = QHBoxLayout()
        top.addWidget(self.load_button)
        top.addWidget(self.file_label, 1)
        top.addWidget(self.save_button)

        data_panel = QWidget()
        data_layout = QVBoxLayout(data_panel)
        data_layout.addWidget(QLabel("Результаты"))
        data_layout.addWidget(self.results_table, 2)
        data_layout.addWidget(QLabel("Ошибки импорта и обработки"))
        data_layout.addWidget(self.error_list, 1)

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(data_panel)
        splitter.addWidget(self.detail_tabs)
        splitter.setSizes((255, 555))

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.addLayout(top)
        layout.addWidget(splitter, 1)
        self.setCentralWidget(central)

        self.load_button.clicked.connect(self.choose_file)
        self.save_button.clicked.connect(self.save_selected_result)
        self.results_table.currentCellChanged.connect(self._show_selected_automaton)

    def choose_file(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите файл с ДКА",
            "",
            "Файлы ДКА (*.txt *.csv *.xlsx *.dot *.gv)",
        )
        if file_path:
            self.load_file(file_path)

    def load_file(self, file_path: str) -> None:
        self.file_label.setText(Path(file_path).name)
        result = self.service.process_file(file_path)
        self._show_result(result)

    def _show_result(self, result: ProcessingResult) -> None:
        self._processed_items = result.items
        self.results_table.setRowCount(len(result.items))
        for row, item in enumerate(result.items):
            values = (
                str(row + 1),
                str(item.source.size),
                str(item.minimized.size),
                str(len(item.source.alphabet)),
            )
            for column, value in enumerate(values):
                self.results_table.setItem(row, column, QTableWidgetItem(value))

        self.error_list.clear()
        for error in result.errors:
            self.error_list.addItem(f"Строка {error.row_number}: {error.message}")

        if result.items:
            self.results_table.selectRow(0)
            self._show_item(result.items[0])
            self.save_button.setEnabled(True)
        else:
            self.chart.clear_view()
            self.transitions_table.setRowCount(0)
            self.classes_table.setRowCount(0)
            self.save_button.setEnabled(False)

    def _show_selected_automaton(
        self,
        current_row: int,
        _current_column: int,
        _previous_row: int,
        _previous_column: int,
    ) -> None:
        """Обновляет пару графов при выборе другой строки результата."""

        if 0 <= current_row < len(self._processed_items):
            self._show_item(self._processed_items[current_row])

    def _show_item(self, item: ProcessedDFA) -> None:
        """Обновляет графы и обе табличные формы выбранного результата."""

        self.chart.show_comparison(item)
        dfa = item.minimized
        transitions = sorted(
            dfa.transitions.items(),
            key=lambda entry: (entry[0][0], entry[0][1], entry[1]),
        )
        self.transitions_table.setRowCount(len(transitions))
        for row, ((source, symbol), target) in enumerate(transitions):
            for column, value in enumerate((source, symbol, target)):
                self.transitions_table.setItem(row, column, QTableWidgetItem(value))

        finals = ", ".join(sorted(dfa.final_states)) or "нет"
        self.transition_info.setText(
            f"Начальное состояние: {dfa.initial_state}   |   Финальные состояния: {finals}"
        )

        class_rows = [
            (class_name, ", ".join(sorted(item.classes[class_name])))
            for class_name in dfa.states
        ]
        class_rows.extend(
            ("— (отброшено)", state)
            for state in sorted(item.discarded_states)
        )
        self.classes_table.setRowCount(len(class_rows))
        for row, values in enumerate(class_rows):
            for column, value in enumerate(values):
                self.classes_table.setItem(row, column, QTableWidgetItem(value))

    def save_selected_result(self) -> None:
        """Сохраняет выбранный независимый ДКА и таблицу его классов."""

        row = self.results_table.currentRow()
        if not 0 <= row < len(self._processed_items):
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить минимизированный ДКА",
            "minimized.csv",
            "CSV (*.csv);;Graphviz DOT (*.dot *.gv)",
        )
        if path:
            export_minimization(self._processed_items[row].minimization, path)
