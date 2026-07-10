"""Минимизация PT-DFA за O(m * lg n) по Валмари и Лехтинену.

Здесь ``n`` - число релевантных состояний, а ``m`` - число заданных
переходов после удаления нерелевантной части автомата.

Код следует не только абстрактному алгоритму из Figure 1 статьи
"Efficient Minimization of DFAs with Partial Transition Functions", но и
его эффективной реализации из Figures 2 и 3:

* ``BRP`` хранит уточняемое разбиение состояний на блоки;
* ``TRP`` хранит уточняемое разбиение переходов на сплиттеры ``(B, a)``;
* рабочие множества содержат только затронутые блоки и сплиттеры;
* после разделения блока просматриваются входящие переходы только меньшей
  половины.

Поэтому код не перебирает весь алфавит для каждого блока и не перестраивает
таблицу ``state -> block`` после каждого split. Каждое состояние и каждый
переход имеют постоянный целочисленный индекс, а принадлежность текущему
блоку узнаётся за O(1).

Как обычно для Python, оценка считает операции со словарями амортизированно
константными. Сами разбиения и рабочие множества реализованы массивами и не
зависят от хеширования.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from math import log2, nan
from typing import Iterable, Iterator

from dfa_app.algorithms.base import AlgorithmMetadata, DFAMinimizer
from dfa_app.domain.models import DFA, TransitionKey


class _RefinablePartition:
    """Уточняемое разбиение из Figure 2 статьи.

    Все элементы представлены целыми числами ``0 .. element_count - 1``.
    Элементы каждого множества лежат в одном непрерывном отрезке массива
    ``_elements``::

        first              marked_boundary                    end
          |                       |                             |
          v                       v                             v
        [ уже отмеченные элементы | ещё не отмеченные элементы )

    ``mark`` за O(1) переставляет элемент на границу отмеченной части.
    ``split`` создаёт из отмеченной части новое множество. Его время линейно
    числу отмеченных элементов, но перед этим каждый из них был отмечен
    отдельным O(1)-вызовом. Поэтому пара операций ``mark + split`` имеет
    амортизированную стоимость O(1) на отметку, как в доказательстве статьи.
    """

    def __init__(self, element_count: int, groups: Iterable[Iterable[int]]) -> None:
        self._elements: list[int] = []
        self._location = [0] * element_count
        self._set_of = [0] * element_count
        self._first: list[int] = []
        self._marked_boundary: list[int] = []
        self._end: list[int] = []

        for set_id, group in enumerate(groups):
            first = len(self._elements)
            for element in group:
                self._location[element] = len(self._elements)
                self._set_of[element] = set_id
                self._elements.append(element)

            end = len(self._elements)
            if first == end:
                raise ValueError("уточняемое разбиение не может содержать пустое множество")

            self._first.append(first)
            self._marked_boundary.append(first)
            self._end.append(end)

        if len(self._elements) != element_count:
            raise ValueError("группы должны образовывать разбиение всех элементов")

    @classmethod
    def one_set(cls, element_count: int) -> _RefinablePartition:
        """Создаёт одно множество со всеми элементами.

        Для пустого множества переходов используется ``from_groups``: BRP
        всегда содержит хотя бы начальное состояние, а TRP может быть пустым.
        """

        return cls(element_count, (range(element_count),))

    @classmethod
    def from_groups(
        cls,
        element_count: int,
        groups: Iterable[Iterable[int]],
    ) -> _RefinablePartition:
        """Создаёт готовое разбиение, например начальные группы TRP по меткам."""

        return cls(element_count, groups)

    @property
    def set_count(self) -> int:
        return len(self._first)

    def set_of(self, element: int) -> int:
        """Возвращает индекс текущего множества элемента за O(1)."""

        return self._set_of[element]

    def size(self, set_id: int) -> int:
        """Возвращает размер множества за O(1)."""

        return self._end[set_id] - self._first[set_id]

    def no_marks(self, set_id: int) -> bool:
        """Проверяет, что в множестве пока нет отмеченных элементов."""

        return self._marked_boundary[set_id] == self._first[set_id]

    def elements(self, set_id: int) -> Iterator[int]:
        """Последовательно выдаёт элементы множества без создания копии."""

        first = self._first[set_id]
        end = self._end[set_id]
        for position in range(first, end):
            yield self._elements[position]

    def mark(self, element: int) -> None:
        """Отмечает элемент для следующего разделения его множества за O(1)."""

        set_id = self._set_of[element]
        position = self._location[element]
        boundary = self._marked_boundary[set_id]

        # Повторная отметка не меняет структуру. В корректном PT-DFA она не
        # нужна, но эта защита делает примитив безопасным и самостоятельным.
        if position < boundary:
            return

        element_at_boundary = self._elements[boundary]
        self._elements[position] = element_at_boundary
        self._location[element_at_boundary] = position
        self._elements[boundary] = element
        self._location[element] = boundary
        self._marked_boundary[set_id] = boundary + 1

    def split(self, set_id: int) -> int | None:
        """Отделяет отмеченные элементы и возвращает индекс нового множества.

        Если ничего не отмечено или отмечено всё множество, реального split нет
        и возвращается ``None``. Во втором случае отметки также снимаются.
        """

        first = self._first[set_id]
        boundary = self._marked_boundary[set_id]
        end = self._end[set_id]

        if boundary == first:
            return None

        if boundary == end:
            self._marked_boundary[set_id] = first
            return None

        # Отмеченная левая часть становится новым множеством. Старый set_id
        # остаётся у правой части: так ожидающий обработки старый сплиттер
        # автоматически сохраняет свой статус в рабочем множестве.
        new_set_id = self.set_count
        self._first.append(first)
        self._marked_boundary.append(first)
        self._end.append(boundary)

        self._first[set_id] = boundary
        self._marked_boundary[set_id] = boundary

        for position in range(first, boundary):
            self._set_of[self._elements[position]] = new_set_id

        return new_set_id


class _IndexWorkSet:
    """Множество целочисленных индексов со стеком и флагами присутствия.

    В отличие от обычного ``set[int]`` эта структура не зависит от хеширования.
    ``add`` и ``pop`` работают за O(1), а один индекс не может попасть в стек
    дважды. Это реализация простых множеств ``Unready_Spls``,
    ``Touched_Blocks`` и ``Touched_Spls`` из Figure 3.
    """

    def __init__(self, capacity: int) -> None:
        self._stack: list[int] = []
        self._present = [False] * capacity

    def __bool__(self) -> bool:
        return bool(self._stack)

    def add(self, index: int) -> None:
        if self._present[index]:
            return
        self._present[index] = True
        self._stack.append(index)

    def pop(self) -> int:
        index = self._stack.pop()
        self._present[index] = False
        return index


@dataclass(frozen=True, slots=True)
class _IndexedPTDFA:
    """PT-DFA в индексном виде, соответствующем массивам Section 4 статьи."""

    state_names: tuple[str, ...]
    state_index: dict[str, int]
    tails: tuple[int, ...]
    labels: tuple[str, ...]
    heads: tuple[int, ...]
    incoming: tuple[tuple[int, ...], ...]
    outgoing: tuple[tuple[int, ...], ...]

    @property
    def state_count(self) -> int:
        return len(self.state_names)

    @property
    def transition_count(self) -> int:
        return len(self.tails)


class PTDFAMinimizer(DFAMinimizer):
    """Минимизирует DFA/PT-DFA алгоритмом Валмари-Лехтинена."""

    @property
    def metadata(self) -> AlgorithmMetadata:
        return AlgorithmMetadata(
            name="PT-DFA минимизация",
            upper_label="O(m·lg n)",
            lower_label="",
            # Текущий контракт графика передаёт только n и размер алфавита, но
            # не передаёт фактическое m. Поэтому численная функция использует
            # безопасную оценку m <= n * |Sigma|. Сам алгоритм ниже работает с
            # фактическими заданными переходами и не сканирует весь алфавит.
            upper_bound=lambda n, alphabet_size: (
                n * alphabet_size * log2(max(n, 2))
            ),
            lower_bound=lambda _n, _alphabet_size: nan,
        )

    def minimize(self, dfa: DFA) -> DFA:
        # Figure 1, строка 1. Это не только оптимизация, но и условие
        # корректности для частичной функции переходов: состояние с пустым
        # правым языком нельзя отличать от отсутствующего перехода.
        states, transitions, final_states = self._remove_irrelevant_parts(dfa)

        # Figure 1, строка 2. Если достижимых финальных состояний нет, язык пуст.
        # Минимальный PT-DFA пустого языка содержит ровно одно состояние и ни
        # одного перехода.
        if not final_states:
            empty_state = "{пустой}"
            return DFA(
                states=(empty_state,),
                alphabet=dfa.alphabet,
                transitions={},
                initial_state=empty_state,
                final_states=frozenset(),
            )

        indexed = self._index_automaton(states, transitions)
        final_indices = frozenset(indexed.state_index[state] for state in final_states)

        # Figures 2 и 3: получаем устойчивое разбиение состояний. После удаления
        # нерелевантных состояний каждое состояние, кроме, возможно, начального,
        # имеет входящий переход. Поэтому n <= m + 1, и линейные по n этапы
        # укладываются в итоговую границу O(m * lg n) для непустого языка.
        blocks = self._refine_blocks(indexed, final_indices)

        # Figure 1, строки 16-21. Строим фактор-автомат только по заданным
        # исходящим переходам представителей, не выполняя цикл по всему Sigma.
        return self._build_minimized_dfa(
            dfa.alphabet,
            indexed,
            indexed.state_index[dfa.initial_state],
            final_indices,
            blocks,
        )

    def _index_automaton(
        self,
        states: tuple[str, ...],
        transitions: dict[TransitionKey, str],
    ) -> _IndexedPTDFA:
        """Преобразует строки состояний и переходы в плотные индексы.

        Для перехода ``t`` массивы ``tails[t]``, ``labels[t]`` и ``heads[t]``
        хранят начало, метку и конец. ``incoming[q]`` соответствует
        ``In_trs[q]`` из статьи. ``outgoing[q]`` нужен только для линейного
        построения результата без просмотра отсутствующих переходов.
        """

        state_index = {state: index for index, state in enumerate(states)}
        tails: list[int] = []
        labels: list[str] = []
        heads: list[int] = []
        incoming: list[list[int]] = [[] for _ in states]
        outgoing: list[list[int]] = [[] for _ in states]

        for (source, symbol), target in transitions.items():
            transition_id = len(tails)
            source_id = state_index[source]
            target_id = state_index[target]

            tails.append(source_id)
            labels.append(symbol)
            heads.append(target_id)
            incoming[target_id].append(transition_id)
            outgoing[source_id].append(transition_id)

        return _IndexedPTDFA(
            state_names=states,
            state_index=state_index,
            tails=tuple(tails),
            labels=tuple(labels),
            heads=tuple(heads),
            incoming=tuple(tuple(items) for items in incoming),
            outgoing=tuple(tuple(items) for items in outgoing),
        )

    def _refine_blocks(
        self,
        indexed: _IndexedPTDFA,
        final_states: frozenset[int],
    ) -> _RefinablePartition:
        """Выполняет block-splitting stage из Figure 3.

        Инварианты:

        * ``blocks`` (BRP) является разбиением состояний;
        * каждый блок ``transition_splitters`` (TRP) содержит все переходы
          некоторого непустого сплиттера ``(B, a)``;
        * ``unready_splitters`` содержит ровно те индексы TRP, которые ещё
          должны участвовать в уточнении.

        Сплиттер заново становится готовым к обработке только для меньшей
        половины разделённого целевого блока. Поэтому размер блока, содержащего
        конец конкретного перехода, каждый раз уменьшается минимум вдвое.
        Один переход просматривается не более ``lg n + 1`` раз на каждом из двух
        основных проходов Figure 3, что и даёт O(m * lg n).
        """

        blocks = _RefinablePartition.one_set(indexed.state_count)

        # Figure 3, строка 15. Изначально все переходы с одинаковой меткой
        # принадлежат сплиттеру (Q, a). Группируем только реально существующие
        # метки, поэтому размер алфавита не входит в этот цикл.
        transition_ids_by_label: dict[str, list[int]] = {}
        for transition_id, label in enumerate(indexed.labels):
            transition_ids_by_label.setdefault(label, []).append(transition_id)

        transition_splitters = _RefinablePartition.from_groups(
            indexed.transition_count,
            transition_ids_by_label.values(),
        )

        unready_splitters = _IndexWorkSet(indexed.transition_count)
        touched_blocks = _IndexWorkSet(indexed.state_count)
        touched_splitters = _IndexWorkSet(indexed.transition_count)

        # Figure 3, строка 16: все начальные непустые сплиттеры необработаны.
        for splitter_id in range(transition_splitters.set_count):
            unready_splitters.add(splitter_id)

        def split_block(block_id: int) -> None:
            """Реализует процедуру Split_block из строк 1-14 Figure 3."""

            marked_block_id = blocks.split(block_id)
            if marked_block_id is None:
                return

            # blocks.split оставляет неотмеченную часть под старым block_id,
            # а отмеченную помещает в marked_block_id. Для обновления TRP
            # просматриваем строго меньшую из двух половин.
            if blocks.size(block_id) <= blocks.size(marked_block_id):
                small_block_id = block_id
            else:
                small_block_id = marked_block_id

            # Figure 3, строки 4-10. Для каждого входящего перехода меньшей
            # половины отмечаем его в текущем TRP-сплиттере. Один переход
            # попадает сюда лишь когда блок его конца уменьшается минимум вдвое.
            for state_id in blocks.elements(small_block_id):
                for transition_id in indexed.incoming[state_id]:
                    splitter_id = transition_splitters.set_of(transition_id)
                    if transition_splitters.no_marks(splitter_id):
                        touched_splitters.add(splitter_id)
                    transition_splitters.mark(transition_id)

            # Figure 3, строки 11-14. TRP.split заменяет старый (C, a) его
            # непустыми наследниками. Новый индекс всегда относится к переходам
            # в меньшую половину, поэтому именно он добавляется в U.
            while touched_splitters:
                splitter_id = touched_splitters.pop()
                small_splitter_id = transition_splitters.split(splitter_id)
                if small_splitter_id is not None:
                    unready_splitters.add(small_splitter_id)

        # Figure 3, строки 17-18: начальное разбиение {F, Q-F}. Если Q=F,
        # split корректно обнаружит, что отмечен весь единственный блок.
        for state_id in final_states:
            blocks.mark(state_id)
        split_block(0)

        # Figure 3, строки 19-29. Обработка сплиттера идёт назад по его
        # переходам и отмечает исходные состояния во всех затронутых блоках.
        while unready_splitters:
            splitter_id = unready_splitters.pop()

            for transition_id in transition_splitters.elements(splitter_id):
                source_id = indexed.tails[transition_id]
                source_block_id = blocks.set_of(source_id)
                if blocks.no_marks(source_block_id):
                    touched_blocks.add(source_block_id)
                blocks.mark(source_id)

            while touched_blocks:
                split_block(touched_blocks.pop())

        return blocks

    def _remove_irrelevant_parts(
        self,
        dfa: DFA,
    ) -> tuple[tuple[str, ...], dict[TransitionKey, str], frozenset[str]]:
        """Удаляет состояния, не влияющие на язык, как в строке 1 Figure 1."""

        reachable = self._reachable_states(dfa)
        productive = self._productive_states(dfa)

        # Точное определение статьи:
        # R = {initial} union (reachable intersect productive).
        relevant = frozenset({dfa.initial_state}) | (reachable & productive)
        transitions = {
            key: target
            for key, target in dfa.transitions.items()
            if key[0] in relevant and target in relevant
        }
        states = tuple(state for state in dfa.states if state in relevant)
        final_states = frozenset(dfa.final_states & relevant)
        return states, transitions, final_states

    def _reachable_states(self, dfa: DFA) -> frozenset[str]:
        """Находит состояния, достижимые из начального, за O(n + m)."""

        outgoing: dict[str, list[str]] = {state: [] for state in dfa.states}
        for (source, _), target in dfa.transitions.items():
            outgoing[source].append(target)

        seen = {dfa.initial_state}
        queue = deque([dfa.initial_state])
        while queue:
            state = queue.popleft()
            for target in outgoing[state]:
                if target not in seen:
                    seen.add(target)
                    queue.append(target)
        return frozenset(seen)

    def _productive_states(self, dfa: DFA) -> frozenset[str]:
        """Находит состояния, из которых достижим финал, за O(n + m)."""

        incoming_sources: dict[str, list[str]] = {state: [] for state in dfa.states}
        for (source, _), target in dfa.transitions.items():
            incoming_sources[target].append(source)

        seen = set(dfa.final_states)
        queue = deque(dfa.final_states)
        while queue:
            state = queue.popleft()
            for source in incoming_sources[state]:
                if source not in seen:
                    seen.add(source)
                    queue.append(source)
        return frozenset(seen)

    def _build_minimized_dfa(
        self,
        alphabet: tuple[str, ...],
        indexed: _IndexedPTDFA,
        initial_state: int,
        final_states: frozenset[int],
        blocks: _RefinablePartition,
    ) -> DFA:
        """Строит минимальный PT-DFA по итоговым блокам за O(n log n + m).

        Сортировка имён нужна только для стабильного человекочитаемого вывода.
        Для релевантного автомата с непустым языком ``n <= m + 1``, поэтому она
        не ухудшает общую оценку O(m * lg n).
        """

        members_by_block = {
            block_id: tuple(
                sorted(
                    blocks.elements(block_id),
                    key=lambda state_id: indexed.state_names[state_id],
                )
            )
            for block_id in range(blocks.set_count)
        }
        base_name_by_block = {
            block_id: self._block_name(
                indexed.state_names[state_id]
                for state_id in state_ids
            )
            for block_id, state_ids in members_by_block.items()
        }

        # Обычно каноническое имя уже уникально. Однако допустимые исходные
        # идентификаторы "a", "b" и "a,b" создают одинаковую строку для блоков
        # {a,b} и {"a,b"}. Суффиксы сохраняют читаемость и гарантируют валидный
        # набор состояний результата.
        ordered_blocks = tuple(
            sorted(
                range(blocks.set_count),
                key=lambda block_id: (
                    base_name_by_block[block_id],
                    tuple(
                        indexed.state_names[state_id]
                        for state_id in members_by_block[block_id]
                    ),
                ),
            )
        )
        block_names: dict[int, str] = {}
        name_occurrences: dict[str, int] = {}
        for block_id in ordered_blocks:
            base_name = base_name_by_block[block_id]
            occurrence = name_occurrences.get(base_name, 0) + 1
            name_occurrences[base_name] = occurrence
            block_names[block_id] = (
                base_name if occurrence == 1 else f"{base_name}#{occurrence}"
            )

        minimized_transitions: dict[TransitionKey, str] = {}
        minimized_final_states: set[str] = set()

        for block_id in ordered_blocks:
            state_ids = members_by_block[block_id]
            representative = state_ids[0]
            source_name = block_names[block_id]

            # Lemma 2.2 гарантирует, что любой представитель имеет ту же
            # картину переходов между блоками. Идём только по существующим
            # переходам представителя - отсутствующие переходы не создаются.
            for transition_id in indexed.outgoing[representative]:
                symbol = indexed.labels[transition_id]
                target_state = indexed.heads[transition_id]
                target_block = blocks.set_of(target_state)
                minimized_transitions[(source_name, symbol)] = block_names[target_block]

            if any(state_id in final_states for state_id in state_ids):
                minimized_final_states.add(source_name)

        initial_block = blocks.set_of(initial_state)
        return DFA(
            states=tuple(block_names[block_id] for block_id in ordered_blocks),
            alphabet=alphabet,
            transitions=minimized_transitions,
            initial_state=block_names[initial_block],
            final_states=frozenset(minimized_final_states),
        )

    def _block_name(self, states: Iterable[str]) -> str:
        """Создаёт привычное каноническое имя блока из отсортированных имён."""

        return "{" + ",".join(states) + "}"


# Обратная совместимость для импортов, существовавших до переименования класса.
PassthroughMinimizer = PTDFAMinimizer
