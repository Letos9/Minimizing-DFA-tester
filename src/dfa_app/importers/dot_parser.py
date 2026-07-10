from __future__ import annotations

import ast
import re

from dfa_app.domain.models import DFA
from dfa_app.domain.validation import DFAValidationError, validate_dfa

_ID = r'("(?:\\.|[^"\\])*"|[A-Za-z_][A-Za-z0-9_]*)'
_NODE_RE = re.compile(rf'^\s*(?P<id>{_ID})\s*(?:\[(?P<attrs>.*)\])?\s*$')
_EDGE_RE = re.compile(rf'^\s*(?P<src>{_ID})\s*->\s*(?P<dst>{_ID})\s*(?:\[(?P<attrs>.*)\])?\s*$')
_ATTR_RE = re.compile(r'([A-Za-z_][A-Za-z0-9_]*)\s*=\s*("(?:\\.|[^"\\])*"|[^,\s]+)')


class DotParseError(ValueError):
    def __init__(self, message: str, line_number: int = 1) -> None:
        self.line_number = line_number
        super().__init__(message)


def _decode(value: str) -> str:
    value = value.strip()
    return str(ast.literal_eval(value)) if value.startswith('"') else value


def _attributes(text: str | None, line_number: int) -> dict[str, str]:
    if not text:
        return {}
    result = {key.lower(): _decode(value) for key, value in _ATTR_RE.findall(text)}
    remainder = _ATTR_RE.sub('', text).replace(',', '').strip()
    if remainder:
        raise DotParseError(f"не удалось разобрать атрибуты: {text}", line_number)
    return result


def _statements(text: str) -> list[tuple[int, str]]:
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
    text = re.sub(r'//.*?$|#.*?$', '', text, flags=re.MULTILINE)
    match = re.search(r'\b(?:strict\s+)?digraph(?:\s+\w+)?\s*\{(.*)\}\s*$', text, re.DOTALL | re.IGNORECASE)
    if not match:
        raise DotParseError("ожидается ориентированный граф 'digraph { ... }'")
    body = match.group(1)
    start_line = text.count('\n', 0, match.start(1)) + 1
    result: list[tuple[int, str]] = []
    current: list[str] = []
    line = start_line
    statement_line = line
    brackets = 0
    quoted = False
    escaped = False
    for char in body:
        if not current and not char.isspace():
            statement_line = line
        if quoted:
            current.append(char)
            if escaped:
                escaped = False
            elif char == '\\':
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
            current.append(char)
        elif char == '[':
            brackets += 1
            current.append(char)
        elif char == ']':
            brackets -= 1
            current.append(char)
        elif (char == ';' or char == '\n') and brackets == 0:
            statement = ''.join(current).strip()
            if statement:
                result.append((statement_line, statement))
            current = []
        else:
            current.append(char)
        if char == '\n':
            line += 1
    statement = ''.join(current).strip()
    if statement:
        result.append((statement_line, statement))
    if quoted or brackets:
        raise DotParseError('незакрытая кавычка или список атрибутов', statement_line)
    return result


def parse_dot(text: str) -> DFA:
    nodes: dict[str, dict[str, str]] = {}
    order: list[str] = []
    edges: list[tuple[str, str, dict[str, str], int]] = []

    def remember(node: str) -> None:
        if node not in order:
            order.append(node)

    for line, statement in _statements(text):
        if re.match(r'^(graph|node|edge)\s*\[', statement, re.IGNORECASE):
            continue
        edge = _EDGE_RE.fullmatch(statement)
        if edge:
            src, dst = _decode(edge.group('src')), _decode(edge.group('dst'))
            remember(src)
            remember(dst)
            edges.append((src, dst, _attributes(edge.group('attrs'), line), line))
            continue
        node = _NODE_RE.fullmatch(statement)
        if node:
            node_id = _decode(node.group('id'))
            remember(node_id)
            nodes.setdefault(node_id, {}).update(_attributes(node.group('attrs'), line))
            continue
        raise DotParseError(f'не удалось разобрать выражение: {statement}', line)

    pseudo = {node for node, attrs in nodes.items() if attrs.get('shape', '').lower() == 'none'}
    pseudo.update(node for node in order if node.startswith('__start'))
    initial_edges = [edge for edge in edges if edge[0] in pseudo and not edge[2].get('label', '').strip()]
    if len(initial_edges) != 1:
        raise DotParseError('должен быть ровно один переход от фиктивной стартовой вершины')

    initial = initial_edges[0][1]
    states = tuple(node for node in order if node not in pseudo)
    finals = frozenset(node for node, attrs in nodes.items() if attrs.get('shape', '').lower() == 'doublecircle')
    alphabet: list[str] = []
    transitions: dict[tuple[str, str], str] = {}

    for src, dst, attrs, line in edges:
        if src in pseudo:
            if (src, dst, attrs, line) != initial_edges[0]:
                raise DotParseError('у стартовой вершины допустим только один переход', line)
            continue
        if dst in pseudo:
            raise DotParseError('переход в фиктивную стартовую вершину недопустим', line)
        symbol = attrs.get('label', '').strip()
        if not symbol:
            raise DotParseError('у перехода отсутствует непустой атрибут label', line)
        key = (src, symbol)
        if key in transitions:
            raise DotParseError(f'переход ({src}, {symbol}) задан более одного раза', line)
        transitions[key] = dst
        if symbol not in alphabet:
            alphabet.append(symbol)

    dfa = DFA(states, tuple(alphabet), transitions, initial, finals)
    try:
        validate_dfa(dfa)
    except DFAValidationError as exc:
        raise DotParseError(str(exc)) from exc
    return dfa
