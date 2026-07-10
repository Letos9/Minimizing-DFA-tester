from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
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

from dfa_app.services.processing import DFAProcessingService, ProcessingResult
from dfa_app.ui.complexity_chart import ComplexityChart


class MainWindow(QMainWindow):
    def __init__(self, service: DFAProcessingService) -> None:
        super().__init__()
        self.service = service
        self.setWindowTitle("Минимизация ДКА")
        self.resize(1100, 760)

        self.load_button = QPushButton("Загрузить файл")
        self.load_button.setObjectName("loadFileButton")
        self.file_label = QLabel("Файл не выбран")
        self.file_label.setObjectName("fileNameLabel")
        self.file_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.results_table = QTableWidget(0, 4)
        self.results_table.setObjectName("resultsTable")
        self.results_table.setHorizontalHeaderLabels(("№", "Состояний до", "Состояний после", "Алфавит"))
        self.results_table.horizontalHeader().setStretchLastSection(True)
        self.error_list = QListWidget()
        self.error_list.setObjectName("errorList")
        self.chart = ComplexityChart()

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
        splitter.setSizes((300, 430))

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.addLayout(top)
        layout.addWidget(splitter, 1)
        self.setCentralWidget(central)

        self.load_button.clicked.connect(self.choose_file)

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
        self.results_table.setRowCount(len(result.items))
        for row, item in enumerate(result.items):
            values = (str(row + 1), str(item.source.size), str(item.minimized.size), str(len(item.source.alphabet)))
            for column, value in enumerate(values):
                self.results_table.setItem(row, column, QTableWidgetItem(value))

        self.error_list.clear()
        for error in result.errors:
            self.error_list.addItem(f"Строка {error.row_number}: {error.message}")

        if result.items:
            self.chart.update_chart(result.items)
        else:
            self.chart.clear_chart()
