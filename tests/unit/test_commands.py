from pathlib import Path

from dfa_app.commands import _project_root


def test_project_root_contains_build_configuration():
    root = _project_root()

    assert root == Path(__file__).resolve().parents[2]
    assert (root / "dfa-app.spec").is_file()

