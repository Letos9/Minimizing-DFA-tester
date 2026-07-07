from __future__ import annotations

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from dfa_app.services.processing import ProcessedDFA


class ComplexityChart(FigureCanvasQTAgg):
    def __init__(self) -> None:
        self.figure = Figure(figsize=(8, 5), tight_layout=True)
        super().__init__(self.figure)
        self.setObjectName("complexityChart")
        self.clear_chart()

    def clear_chart(self) -> None:
        self.figure.clear()
        sizes = self.figure.subplots()
        sizes.set_title("Размер ДКА")
        sizes.set_xlabel("Число состояний входного ДКА")
        sizes.set_ylabel("Число состояний")
        self.draw_idle()

    def update_chart(self, items: tuple[ProcessedDFA, ...]) -> None:
        self.figure.clear()
        sizes = self.figure.subplots()
        ordered = sorted(items, key=lambda item: item.source.size)
        x = [item.source.size for item in ordered]
        before = [item.source.size for item in ordered]
        after = [item.minimized.size for item in ordered]

        sizes.plot(x, before, "o-", label="До минимизации")
        sizes.plot(x, after, "s-", label="После минимизации")
        sizes.set(title="Размер ДКА", xlabel="Число состояний входного ДКА", ylabel="Число состояний")
        sizes.legend()
        sizes.grid(True, alpha=0.3)
        self.figure.tight_layout()
        self.draw_idle()
