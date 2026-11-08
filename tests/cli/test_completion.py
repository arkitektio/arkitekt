"""Shell completion of values: an app's actions, its flavours, its services."""

from pathlib import Path
from typing import Any

from arkitekt.cli.completion import complete_actions, complete_flavours, complete_services

APP = (
    "from arkitekt import App\n"
    "app = App('completed', '1.0.0')\n"
    "print('what the app says at import')\n\n"
    "@app.action\n"
    "def add(a: int) -> int:\n"
    "    return a\n\n"
    "@app.action\n"
    "def addmore(a: int) -> int:\n"
    "    return a\n\n"
    "@app.action\n"
    "def blur(a: int) -> int:\n"
    "    return a\n"
)


class _Ctx:
    """What a completer is handed: the line parsed so far, before any callback."""

    def __init__(self, work_dir: Path, **params: Any) -> None:  # noqa: ANN401
        self.params = params
        self._root = type("Root", (), {"params": {"work_dir": str(work_dir)}})()

    def find_root(self) -> Any:  # noqa: ANN401
        return self._root


def test_an_apps_actions_complete_by_name(tmp_path: Path, capsys) -> None:
    (tmp_path / "completed_app.py").write_text(APP)
    ctx = _Ctx(tmp_path, target="completed_app")

    assert complete_actions(ctx, "ad") == ["add", "addmore"]  # pyright: ignore[reportArgumentType]
    assert complete_actions(ctx, "") == ["add", "addmore", "blur"]  # pyright: ignore[reportArgumentType]
    assert capsys.readouterr().out == "", "what the app prints never reaches the shell"


def test_a_folder_without_an_app_completes_nothing(tmp_path: Path) -> None:
    assert complete_actions(_Ctx(tmp_path), "") == []  # pyright: ignore[reportArgumentType]
    assert complete_services(_Ctx(tmp_path), "") == []  # pyright: ignore[reportArgumentType]


def test_an_app_that_fails_to_import_completes_nothing(tmp_path: Path) -> None:
    (tmp_path / "broken_app.py").write_text("raise SystemExit(3)\n")

    assert complete_actions(_Ctx(tmp_path, target="broken_app"), "") == []  # pyright: ignore[reportArgumentType]


def test_flavours_complete_from_the_work_dir(tmp_path: Path) -> None:
    for name in ("vanilla", "gpu", "gpu-large"):
        (tmp_path / ".arkitekt" / "flavours" / name).mkdir(parents=True)

    assert complete_flavours(_Ctx(tmp_path), "gp") == ["gpu", "gpu-large"]  # pyright: ignore[reportArgumentType]
    assert complete_flavours(_Ctx(tmp_path / "nowhere"), "") == []  # pyright: ignore[reportArgumentType]
