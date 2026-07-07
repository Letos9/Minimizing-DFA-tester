from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def _project_root() -> Path:
    current = Path.cwd().resolve()
    for candidate in (current, *current.parents):
        if (candidate / "pyproject.toml").is_file() and (candidate / "dfa-app.spec").is_file():
            return candidate
    raise RuntimeError("Запустите команду run из каталога проекта DFA")


def _run_module(module: str, *arguments: str) -> int:
    return subprocess.call([sys.executable, "-m", module, *arguments], cwd=_project_root())


def main() -> int:
    parser = argparse.ArgumentParser(prog="run", description="Команды проекта DFA")
    parser.add_argument("command", choices=("app", "test", "build"))
    args = parser.parse_args()

    if args.command == "app":
        from dfa_app.application import main as run_application

        return run_application()
    if args.command == "test":
        return _run_module("pytest")

    root = _project_root()
    result = subprocess.call(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            "--clean",
            "--noconfirm",
            "--distpath",
            str(root / "release"),
            str(root / "dfa-app.spec"),
        ],
        cwd=root,
    )
    if result == 0:
        print(f"Готовый EXE: {root / 'release' / 'DFA-Minimizer.exe'}")
    return result


if __name__ == "__main__":
    raise SystemExit(main())

