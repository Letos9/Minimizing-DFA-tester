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
    QVBoxLayout,
    QWidget,
)

from dfa_app.services.processing import DFAProcessingService, ProcessedDFA, ProcessingResult
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
        self.results_table = QTableWidget(0, 4)
        self.results_table.setObjectName("resultsTable")
        self.results_table.setHorizontalHeaderLabels(("№", "Состояний до", "Состояний после", "Алфавит"))
        self.results_table.horizontalHeader().setStretchLastSection(True)
        self.results_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.results_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.error_list = QListWidget()
        self.error_list.setObjectName("errorList")
        self.chart = AutomataGraphView()

        top = QHBoxLayout()
        top.addWidget(self.load_button)
        top.addWidget(self.file_label, 1)

        data_panel = QWidget()
        data_layout = QVBoxLayout(data_panel)
        data_layout.addWidget(QLabel("Результаты"))
        data_layout.addWidget(self.results_table, 2)
        data_layout.addWidget(QLabel("Ошибки импорта и обработки"))
        data_layout.addWidget(self.error_list, 1)

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(data_panel)
        splitter.addWidget(self.chart)
        splitter.setSizes((255, 555))

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.addLayout(top)
        layout.addWidget(splitter, 1)
        self.setCentralWidget(central)

        self.load_button.clicked.connect(self.choose_file)
        self.results_table.currentCellChanged.connect(self._show_selected_automaton)

    def choose_file(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите файл с ДКА",
            "",
            "Файлы ДКА (*.txt *.csv *.xlsx)",
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
            values = (str(row + 1), str(item.source.size), str(item.minimized.size), str(len(item.source.alphabet)))
            for column, value in enumerate(values):
                self.results_table.setItem(row, column, QTableWidgetItem(value))

        self.error_list.clear()
        for error in result.errors:
            self.error_list.addItem(f"Строка {error.row_number}: {error.message}")

        if result.items:
            self.results_table.selectRow(0)
            self.chart.show_comparison(result.items[0])
        else:
            self.chart.clear_view()

    def _show_selected_automaton(
        self,
        current_row: int,
        _current_column: int,
        _previous_row: int,
        _previous_column: int,
    ) -> None:
        """Обновляет пару графов при выборе другой строки результата."""

        if 0 <= current_row < len(self._processed_items):
            self.chart.show_comparison(self._processed_items[current_row])
