"""Парная визуализация исходного и минимизированного автоматов."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from math import cos, hypot, pi, sin
from textwrap import wrap

from matplotlib.axes import Axes
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from matplotlib.patches import Circle, FancyArrowPatch

from dfa_app.domain.models import DFA
from dfa_app.services.processing import ProcessedDFA

Position = tuple[float, float]
Polyline = tuple[Position, ...]
LabelBox = tuple[float, float, float, float]


@dataclass(frozen=True, slots=True)
class _EdgeLabel:
    """Подпись и дискретизированная траектория соответствующей стрелки."""

    text: str
    path: Polyline


class AutomataGraphView(FigureCanvasQTAgg):
    """Показывает исходный DFA слева, а минимизированный справа.

    Отрисовка сделана непосредственно средствами Matplotlib. Это позволяет не
    добавлять тяжёлую зависимость только ради раскладки небольших графов и
    оставляет все правила изображения в одном хорошо проверяемом месте.
    """

    # После 15 состояний круговая схема перестаёт быть читаемой: узлы, стрелки
    # и подписи начинают сливаться. Большие автоматы показываются сводкой.
    MAX_DRAWN_STATES = 15

    def __init__(self) -> None:
        self.figure = Figure(figsize=(11, 5.5))
        self.figure.set_facecolor("#f8fafc")
        super().__init__(self.figure)
        self.setObjectName("automataGraphView")
        self.clear_view()

    def clear_view(self) -> None:
        """Показывает пустые панели до загрузки корректного автомата."""

        self.figure.clear()
        source_axes, minimized_axes, classes_axes = self._create_axes()
        self._show_placeholder(source_axes, "Исходный автомат")
        self._show_placeholder(minimized_axes, "Минимизированный автомат")
        self._show_placeholder(classes_axes, "Состав новых состояний")
        self.draw_idle()

    def show_comparison(self, item: ProcessedDFA) -> None:
        """Перерисовывает обе панели для одной выбранной строки результата."""

        self.figure.clear()
        source_axes, minimized_axes, classes_axes = self._create_axes()
        display_names = {
            state: f"M{index}"
            for index, state in enumerate(item.minimized.states)
        }

        self._draw_automaton(
            source_axes,
            item.source,
            title=f"Исходный автомат · {item.source.size} сост.",
            node_color="#dbeafe",
            border_color="#2563eb",
        )
        self._draw_automaton(
            minimized_axes,
            item.minimized,
            title=f"Минимизированный · {item.minimized.size} сост.",
            node_color="#dcfce7",
            border_color="#16a34a",
            display_names=display_names,
        )
        self._draw_classes_table(classes_axes, item.minimized, display_names)

        # Явные поля стабильнее tight_layout для сочетания квадратных графов и
        # таблицы: автоматическая компоновка могла обрезать заголовки сверху.
        self.figure.subplots_adjust(
            left=0.035,
            right=0.985,
            bottom=0.08,
            top=0.91,
            wspace=0.22,
        )
        self._align_panel_titles(source_axes, minimized_axes, classes_axes)
        self.draw_idle()

    def _align_panel_titles(self, *panels: Axes) -> None:
        """Создаёт единый ряд заголовков в координатах всей фигуры."""

        # Нельзя переносить сам объект Axes.title в другую систему координат:
        # backend Qt/Matplotlib может некорректно очистить холст при resize.
        # Вместо этого штатные заголовки скрываются, а видимые надписи создаются
        # как Figure.text. Их вертикаль общая и не зависит от aspect панелей.
        title_y = 0.90
        for axes in panels:
            title_text = axes.get_title()
            axes.title.set_visible(False)
            box = axes.get_position(original=True)
            self.figure.text(
                box.x0 + box.width / 2,
                title_y,
                title_text,
                ha="center",
                va="center",
                fontsize=13,
                fontweight="semibold",
            )

    def _create_axes(self) -> tuple[Axes, Axes, Axes]:
        """Создаёт две панели графов и правую панель таблицы соответствий."""

        grid = self.figure.add_gridspec(1, 3, width_ratios=(1.0, 1.0, 0.72))
        return (
            self.figure.add_subplot(grid[0, 0]),
            self.figure.add_subplot(grid[0, 1]),
            self.figure.add_subplot(grid[0, 2]),
        )

    def _show_placeholder(self, axes: Axes, title: str) -> None:
        axes.set_title(title, fontsize=13, fontweight="semibold", pad=14)
        axes.text(
            0.5,
            0.5,
            "Загрузите файл с автоматами",
            ha="center",
            va="center",
            color="#64748b",
            fontsize=11,
            transform=axes.transAxes,
        )
        axes.set_axis_off()

    def _draw_automaton(
        self,
        axes: Axes,
        dfa: DFA,
        *,
        title: str,
        node_color: str,
        border_color: str,
        display_names: dict[str, str] | None = None,
    ) -> None:
        """Рисует один DFA с начальными, финальными состояниями и переходами."""

        axes.set_title(title, fontsize=13, fontweight="semibold", pad=14)
        axes.set_aspect("equal")
        # Дополнительное поле вокруг круговой раскладки зарезервировано под
        # подписи петель и рёбер. За счёт этого текст не приходится ставить
        # поверх окружностей состояний.
        axes.set_xlim(-1.65, 1.65)
        axes.set_ylim(-1.65, 1.65)
        axes.set_axis_off()

        transition_count = len(dfa.transitions)
        if dfa.size > self.MAX_DRAWN_STATES:
            self._show_large_automaton_summary(
                axes,
                dfa,
                transition_count,
                border_color,
            )
            return

        detailed = True
        positions = self._circular_positions(dfa.states)
        node_radius = self._node_radius(dfa.size)

        # Сначала создаём окружности, чтобы рёбра могли использовать их как
        # границы: FancyArrowPatch тогда заканчивает стрелку у края состояния,
        # а не проводит её сквозь подпись до центра.
        node_patches: dict[str, Circle] = {}
        for state in dfa.states:
            x, y = positions[state]
            node = Circle(
                (x, y),
                node_radius,
                facecolor=node_color,
                edgecolor=border_color,
                linewidth=2.0,
                zorder=3,
            )
            axes.add_patch(node)
            node_patches[state] = node

            # По стандартному обозначению финальное состояние получает вторую
            # окружность. Внутренняя линия не перекрывает входящие стрелки.
            if state in dfa.final_states:
                axes.add_patch(
                    Circle(
                        (x, y),
                        node_radius * 0.82,
                        fill=False,
                        edgecolor=border_color,
                        linewidth=1.4,
                        zorder=4,
                    )
                )

            # В среднем режиме подписи узлов сохраняются только пока они ещё
            # различимы. Для десятков мелких окружностей текст создаёт больше
            # шума и объектов Matplotlib, чем полезной информации.
            if detailed or dfa.size <= 60:
                axes.text(
                    x,
                    y,
                    self._display_state_name(
                        display_names.get(state, state) if display_names else state
                    ),
                    ha="center",
                    va="center",
                    fontsize=self._label_font_size(dfa.size),
                    color="#0f172a",
                    zorder=5,
                )

        grouped_transitions: dict[tuple[str, str], list[str]] = defaultdict(list)
        for (source, symbol), target in dfa.transitions.items():
            grouped_transitions[(source, target)].append(symbol)

        protected_paths: list[Polyline] = []
        edge_labels: list[_EdgeLabel] = []

        # Сначала рисуем все линии и запоминаем их приближённую геометрию.
        # Подписи размещаются отдельным проходом, когда известны уже все линии,
        # поэтому они могут избегать не только своего, но и соседних рёбер.
        for (source, target), symbols in grouped_transitions.items():
            label = self._display_edge_label(", ".join(sorted(symbols)))
            if source == target:
                loop_path = self._draw_loop(
                    axes,
                    positions[source],
                    node_radius,
                    border_color,
                    avoid_left=source == dfa.initial_state,
                )
                if detailed:
                    protected_paths.append(loop_path)
                    edge_labels.append(_EdgeLabel(label, loop_path))
                continue

            reverse_exists = (target, source) in grouped_transitions
            curvature = 0.18 if reverse_exists else 0.0
            arrow = FancyArrowPatch(
                positions[source],
                positions[target],
                patchA=node_patches[source],
                patchB=node_patches[target],
                arrowstyle="-|>",
                mutation_scale=13 if detailed else 7,
                connectionstyle=f"arc3,rad={curvature}",
                color="#475569",
                linewidth=1.5 if detailed else 0.65,
                alpha=1.0 if detailed else 0.55,
                zorder=2,
            )
            axes.add_patch(arrow)
            if detailed:
                edge_path = self._sample_edge_path(
                    positions[source],
                    positions[target],
                    curvature,
                )
                protected_paths.append(edge_path)
                edge_labels.append(_EdgeLabel(label, edge_path))

        initial_path = self._draw_initial_arrow(
            axes,
            positions[dfa.initial_state],
            node_radius,
            border_color,
        )
        if detailed:
            protected_paths.append(initial_path)

        # Окружности состояний сразу считаются занятыми прямоугольниками.
        # Небольшой запас запрещает подписи вплотную прижиматься к контуру.
        if detailed:
            occupied: list[LabelBox] = [
                (
                    x - node_radius * 1.35,
                    y - node_radius * 1.35,
                    x + node_radius * 1.35,
                    y + node_radius * 1.35,
                )
                for x, y in positions.values()
            ]

            for edge_label in edge_labels:
                self._draw_edge_label(
                    axes,
                    edge_label,
                    occupied,
                    protected_paths,
                )

        axes.text(
            0.5,
            -0.02,
            "→ начальное   ◎ финальное",
            transform=axes.transAxes,
            ha="center",
            va="top",
            fontsize=8.5,
            color="#64748b",
        )

    def _draw_classes_table(
        self,
        axes: Axes,
        minimized: DFA,
        display_names: dict[str, str],
    ) -> None:
        """Расшифровывает короткие имена состояний минимизированного ДКА."""

        axes.set_title(
            "Состав новых состояний",
            fontsize=13,
            fontweight="semibold",
            pad=14,
        )
        axes.set_axis_off()
        if minimized.size > self.MAX_DRAWN_STATES:
            axes.text(
                0.5,
                0.58,
                "Таблица классов доступна\n"
                "для автоматов до 15 состояний",
                transform=axes.transAxes,
                ha="center",
                va="center",
                fontsize=10,
                color="#64748b",
            )
            return

        rows = [
            (display_names[state], self._class_members_text(state))
            for state in minimized.states
        ]
        table = axes.table(
            cellText=rows,
            colLabels=("Новое", "Исходные состояния"),
            colWidths=(0.28, 0.72),
            cellLoc="left",
            colLoc="left",
            # Таблица занимает отдельную область ниже заголовка. Явный bbox
            # не позволяет шапке подняться и наложиться на заголовок панели.
            bbox=(0.0, 0.03, 1.0, 0.72),
        )
        table.auto_set_font_size(False)
        table.set_fontsize(8.5)
        # Высоту каждой строки определяет число строк текста. Общая сумма
        # ограничена высотой панели, поэтому даже длинные классы не выходят за
        # нижнюю границу таблицы.
        line_counts = [max(1, members.count("\n") + 1) for _, members in rows]
        total_units = 1.15 + sum(line_counts)
        header_height = 0.82 * 1.15 / total_units
        for (row, _column), cell in table.get_celld().items():
            cell.set_edgecolor("#cbd5e1")
            cell.set_linewidth(0.6)
            cell.set_facecolor("#e2e8f0" if row == 0 else "#ffffff")
            if row == 0:
                cell.set_height(header_height)
                cell.get_text().set_fontweight("semibold")
            else:
                cell.set_height(0.82 * line_counts[row - 1] / total_units)

    def _class_members_text(self, canonical_name: str) -> str:
        """Преобразует каноническое ``{q0,q1}#2`` в ``q0, q1``."""

        base_name = canonical_name.rsplit("#", 1)[0]
        if base_name.startswith("{") and base_name.endswith("}"):
            base_name = base_name[1:-1]
        readable_name = base_name.replace(",", ", ")
        return "\n".join(
            wrap(
                readable_name,
                width=25,
                break_long_words=True,
                break_on_hyphens=False,
            )
        )

    def _show_large_automaton_summary(
        self,
        axes: Axes,
        dfa: DFA,
        transition_count: int,
        color: str,
    ) -> None:
        """Показывает безопасную сводку вместо тысяч графических объектов."""

        axes.text(
            0.5,
            0.62,
            "ДКА содержит больше 15 состояний\nи не выводится в виде графа",
            transform=axes.transAxes,
            ha="center",
            va="center",
            fontsize=15,
            fontweight="semibold",
            color="#0f172a",
        )
        axes.text(
            0.5,
            0.43,
            (
                f"Состояний: {dfa.size:,}\n"
                f"Переходов: {transition_count:,}\n"
                f"Финальных: {len(dfa.final_states):,}"
            ).replace(",", " "),
            transform=axes.transAxes,
            ha="center",
            va="center",
            fontsize=12,
            color=color,
            linespacing=1.5,
        )
        axes.text(
            0.5,
            0.23,
            "Минимизация выполнена.\n"
            "Ограничение сохраняет схему читаемой\n"
            "и защищает интерфейс от перегрузки.",
            transform=axes.transAxes,
            ha="center",
            va="center",
            fontsize=9.5,
            color="#64748b",
            wrap=True,
        )

    def _draw_loop(
        self,
        axes: Axes,
        position: Position,
        node_radius: float,
        color: str,
        *,
        avoid_left: bool,
    ) -> Polyline:
        """Рисует петлю наружу от центра графа, в свободную область."""

        x, y = position
        distance = hypot(x, y)
        if distance:
            outward_x, outward_y = x / distance, y / distance
        else:
            outward_x, outward_y = 0.0, 1.0

        # У самого левого начального состояния наружное направление совпало бы
        # с начальной стрелкой. В таком частном случае уводим петлю вверх.
        if avoid_left and outward_x < -0.55:
            outward_x, outward_y = 0.0, 1.0

        # Направление выбирается по часовой стрелке: при rad=-1.5 дуга arc3
        # тогда изгибается именно в сторону outward, а не прячется под узлом.
        tangent_x, tangent_y = outward_y, -outward_x
        base_x = x + outward_x * node_radius * 0.78
        base_y = y + outward_y * node_radius * 0.78
        start = (
            base_x - tangent_x * node_radius * 0.55,
            base_y - tangent_y * node_radius * 0.55,
        )
        end = (
            base_x + tangent_x * node_radius * 0.55,
            base_y + tangent_y * node_radius * 0.55,
        )
        axes.add_patch(
            FancyArrowPatch(
                start,
                end,
                arrowstyle="-|>",
                mutation_scale=12,
                connectionstyle="arc3,rad=-1.5",
                color=color,
                linewidth=1.4,
                zorder=2,
            )
        )

        # Квадратичная кривая приближает ConnectionStyle arc3. Её середина
        # лежит снаружи круговой раскладки и используется для подписи петли.
        control_x = x + outward_x * node_radius * 2.8
        control_y = y + outward_y * node_radius * 2.8
        return tuple(
            (
                (1 - t) ** 2 * start[0]
                + 2 * (1 - t) * t * control_x
                + t**2 * end[0],
                (1 - t) ** 2 * start[1]
                + 2 * (1 - t) * t * control_y
                + t**2 * end[1],
            )
            for t in (step / 20 for step in range(21))
        )

    def _draw_edge_label(
        self,
        axes: Axes,
        edge: _EdgeLabel,
        occupied: list[LabelBox],
        protected_paths: list[Polyline],
    ) -> None:
        """Ставит входной символ непосредственно поверх своей стрелки."""

        # Сначала пробуем точную середину стрелки, затем симметричные точки
        # немного раньше и позже. Все кандидаты лежат на самой траектории.
        last_index = len(edge.path) - 1
        candidate_indices = (
            round(last_index * 0.50),
            round(last_index * 0.42),
            round(last_index * 0.58),
            round(last_index * 0.34),
            round(last_index * 0.66),
        )
        candidates = tuple(edge.path[index] for index in candidate_indices)

        # Собственную линию намеренно исключаем из запретов: белая подложка
        # подписи делает аккуратный разрыв стрелки под входным символом. Другие
        # стрелки, состояния и подписи по-прежнему считаются препятствиями.
        other_paths = [
            path
            for path in protected_paths
            if path is not edge.path
        ]

        self._place_label(
            axes,
            edge.text,
            candidates,
            occupied,
            other_paths,
        )

    def _place_label(
        self,
        axes: Axes,
        text: str,
        candidates: tuple[Position, ...],
        occupied: list[LabelBox],
        protected_paths: list[Polyline],
    ) -> None:
        """Выбирает кандидата без пересечений с фигурами, линиями и текстом."""

        best_position = candidates[0]
        best_box = self._label_box(best_position, text)
        best_penalty = float("inf")

        for candidate_index, position in enumerate(candidates):
            label_box = self._label_box(position, text)
            half_width = (label_box[2] - label_box[0]) / 2
            half_height = (label_box[3] - label_box[1]) / 2
            clearance = hypot(half_width, half_height) + 0.035

            outside = (
                label_box[0] < -1.50
                or label_box[2] > 1.50
                or label_box[1] < -1.47
                or label_box[3] > 1.47
            )
            overlapping_boxes = sum(
                self._boxes_overlap(label_box, other)
                for other in occupied
            )
            nearest_line = min(
                (
                    self._distance_to_polyline(position, path)
                    for path in protected_paths
                ),
                default=float("inf"),
            )
            line_overlap = nearest_line < clearance

            # Большие коэффициенты делают отсутствие пересечений главным
            # критерием; расстояние от первого кандидата лишь стабилизирует
            # выбор между несколькими одинаково безопасными позициями.
            penalty = (
                10_000 * outside
                + 1_000 * overlapping_boxes
                + 500 * line_overlap
                + candidate_index * 0.01
            )
            if penalty < best_penalty:
                best_penalty = penalty
                best_position = position
                best_box = label_box
            if penalty < 1:
                break

        occupied.append(best_box)
        axes.text(
            *best_position,
            text,
            ha="center",
            va="center",
            fontsize=8.5,
            color="#334155",
            bbox={
                "boxstyle": "round,pad=0.18",
                "fc": "white",
                "ec": "#e2e8f0",
                "linewidth": 0.5,
                "alpha": 0.97,
            },
            zorder=6,
        )

    def _label_box(self, position: Position, text: str) -> LabelBox:
        """Приближённо оценивает рамку текста в координатах графа."""

        lines = text.splitlines() or [""]
        half_width = max(0.055, max(map(len, lines)) * 0.022 + 0.025)
        half_height = len(lines) * 0.052 + 0.025
        x, y = position
        return (x - half_width, y - half_height, x + half_width, y + half_height)

    def _boxes_overlap(self, first: LabelBox, second: LabelBox) -> bool:
        margin = 0.025
        return not (
            first[2] + margin < second[0]
            or first[0] - margin > second[2]
            or first[3] + margin < second[1]
            or first[1] - margin > second[3]
        )

    def _sample_edge_path(
        self,
        source: Position,
        target: Position,
        curvature: float,
    ) -> Polyline:
        """Дискретизирует прямую или дугу для проверки близости подписей."""

        source_x, source_y = source
        target_x, target_y = target
        delta_x = target_x - source_x
        delta_y = target_y - source_y
        length = hypot(delta_x, delta_y) or 1.0
        midpoint = (
            (source_x + target_x) / 2 - delta_y / length * curvature * length,
            (source_y + target_y) / 2 + delta_x / length * curvature * length,
        )

        return tuple(
            (
                (1 - t) ** 2 * source_x
                + 2 * (1 - t) * t * midpoint[0]
                + t**2 * target_x,
                (1 - t) ** 2 * source_y
                + 2 * (1 - t) * t * midpoint[1]
                + t**2 * target_y,
            )
            for t in (step / 20 for step in range(21))
        )

    def _distance_to_polyline(self, point: Position, path: Polyline) -> float:
        return min(
            self._distance_to_segment(point, start, end)
            for start, end in zip(path, path[1:])
        )

    def _distance_to_segment(
        self,
        point: Position,
        start: Position,
        end: Position,
    ) -> float:
        """Возвращает евклидово расстояние от точки до отрезка."""

        point_x, point_y = point
        start_x, start_y = start
        end_x, end_y = end
        delta_x = end_x - start_x
        delta_y = end_y - start_y
        squared_length = delta_x * delta_x + delta_y * delta_y
        if not squared_length:
            return hypot(point_x - start_x, point_y - start_y)

        projection = (
            (point_x - start_x) * delta_x + (point_y - start_y) * delta_y
        ) / squared_length
        projection = min(1.0, max(0.0, projection))
        nearest_x = start_x + projection * delta_x
        nearest_y = start_y + projection * delta_y
        return hypot(point_x - nearest_x, point_y - nearest_y)

    def _draw_initial_arrow(
        self,
        axes: Axes,
        position: Position,
        node_radius: float,
        color: str,
    ) -> Polyline:
        """Добавляет входящую извне стрелку к начальному состоянию."""

        x, y = position
        # Начальная стрелка всегда входит слева. Так обозначение остаётся
        # предсказуемым и не пересекается с петлёй, которую мы рисуем сверху.
        start = (x - node_radius * 2.6, y)
        end = (x - node_radius * 1.08, y)
        axes.add_patch(
            FancyArrowPatch(
                start,
                end,
                arrowstyle="-|>",
                mutation_scale=14,
                color=color,
                linewidth=1.8,
                zorder=4,
            )
        )
        return (start, end)

    def _circular_positions(self, states: tuple[str, ...]) -> dict[str, Position]:
        """Возвращает детерминированную круговую раскладку в порядке states."""

        if len(states) == 1:
            return {states[0]: (0.0, 0.0)}

        radius = 0.95
        return {
            state: (
                radius * cos(pi / 2 - 2 * pi * index / len(states)),
                radius * sin(pi / 2 - 2 * pi * index / len(states)),
            )
            for index, state in enumerate(states)
        }

    def _node_radius(self, state_count: int) -> float:
        if state_count <= 8:
            return 0.16
        if state_count <= 14:
            return 0.12
        # Радиус уменьшается вместе с расстоянием между точками окружности,
        # иначе в упрощённом режиме соседние состояния перекрывают друг друга.
        return max(0.018, min(0.09, 2.4 / state_count))

    def _label_font_size(self, state_count: int) -> float:
        if state_count <= 8:
            return 9.5
        if state_count <= 14:
            return 8.0
        return 6.5

    def _display_state_name(self, state: str) -> str:
        """Переносит длинное имя блока, не изменяя само состояние DFA."""

        if len(state) <= 14:
            return state
        return "\n".join(wrap(state, width=14, break_long_words=True))

    def _display_edge_label(self, label: str) -> str:
        """Переносит длинный список символов, уменьшая ширину подписи."""

        if len(label) <= 18:
            return label
        return "\n".join(wrap(label, width=18, break_long_words=False))
