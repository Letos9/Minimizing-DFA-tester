from pathlib import Path

from dfa_app.algorithms.base import AlgorithmMetadata, DFAMinimizer
from dfa_app.domain.models import DFA
from dfa_app.services.processing import DFAProcessingService


class RecordingMinimizer(DFAMinimizer):
    def __init__(self, fail: bool = False) -> None:
        self.calls = 0
        self.fail = fail

    @property
    def metadata(self) -> AlgorithmMetadata:
        return AlgorithmMetadata("test", "O(n²)", "Ω(n)", lambda n, _: n * n, lambda n, _: n)

    def minimize(self, dfa: DFA) -> DFA:
        self.calls += 1
        if self.fail:
            raise RuntimeError("boom")
        return dfa


def make_file(path: Path) -> None:
    path.write_text(
        "states;alphabet;transitions;initial;finals\n"
        "q0|q1;0;q0,0->q1|q1,0->q1;q0;q1\n",
        encoding="utf-8",
    )


def test_service_calls_algorithm_for_each_valid_dfa(tmp_path: Path):
    path = tmp_path / "input.csv"
    make_file(path)
    algorithm = RecordingMinimizer()

    result = DFAProcessingService(algorithm).process_file(path)

    assert algorithm.calls == 1
    assert len(result.items) == 1
    assert result.metadata.name == "test"


def test_service_converts_algorithm_exception_to_row_error(tmp_path: Path):
    path = tmp_path / "input.csv"
    make_file(path)

    result = DFAProcessingService(RecordingMinimizer(fail=True)).process_file(path)

    assert not result.items
    assert "ошибка алгоритма: boom" in result.errors[0].message

