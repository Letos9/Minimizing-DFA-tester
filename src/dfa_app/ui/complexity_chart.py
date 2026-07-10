"""Совместимость со старым импортом виджета графика сложности.

Новый интерфейс использует :class:`AutomataGraphView`. Псевдоним оставлен,
чтобы внешние импорты прежнего имени не ломались сразу после обновления.
"""

from dfa_app.ui.automata_graph import AutomataGraphView

ComplexityChart = AutomataGraphView
