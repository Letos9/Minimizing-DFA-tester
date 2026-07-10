from __future__ import annotations

import sys

from PyQt6.QtWidgets import QApplication

from dfa_app.algorithms.pt_dfa_minimizer import PTDFAMinimizer
from dfa_app.services.processing import DFAProcessingService
from dfa_app.ui.main_window import MainWindow


def create_window() -> MainWindow:
    service = DFAProcessingService(PTDFAMinimizer())
    return MainWindow(service)


def main() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    window = create_window()
    window.show()
    return app.exec()
