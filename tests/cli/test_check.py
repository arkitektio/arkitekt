"""`arkitekt check`, and what any command says when the app does not import."""

import pytest
from typer.testing import CliRunner

from arkitekt.cli.main import cli_app

VALID = (
    "from arkitekt import App\n"
    "app = App('checked', '1.2.3')\n\n"
    "@app.action\n"
    "def add(a: int, b: int = 2) -> int:\n"
    "    return a + b\n"
)

UNTYPED = (
    "from arkitekt import App\n"
    "app = App('checked', '1.2.3')\n\n"
    "@app.action\n"
    "def add(a, b: int = 2) -> int:\n"
    "    return a + b\n"
)

UNCLOSED = "from arkitekt import App\napp = App('checked', '1.2.3'\n"

RAISING_HELPER = "from arkitekt import App\nimport checkhelper\napp = App('checked', '1.2.3')\n"


def _invoke(work_dir, *args):
    return CliRunner().invoke(cli_app, ["--work-dir", str(work_dir), *args])


def test_check_says_what_a_valid_app_declares(tmp_path):
    (tmp_path / "app.py").write_text(VALID)

    result = _invoke(tmp_path, "check")

    assert result.exit_code == 0, result.output
    assert "checked 1.2.3 is valid" in result.output
    assert "1 action" in result.output


def test_check_connects_to_nothing(tmp_path, monkeypatch):
    def never(*args, **kwargs):
        raise AssertionError("check connected")

    monkeypatch.setattr("arkitekt.runtime.connect", never)
    monkeypatch.setattr("arkitekt.runtime.build_fakts", never)
    (tmp_path / "app.py").write_text(VALID)

    assert _invoke(tmp_path, "check").exit_code == 0


@pytest.mark.parametrize("command", [["check"], ["run", "prod"], ["inspect", "all"], ["status"]])
@pytest.mark.parametrize(
    ("source", "where", "why"),
    [
        (UNTYPED, "app.py:4", "type hint for a"),
        (UNCLOSED, "app.py:2", "never closed"),
    ],
)
def test_an_app_that_does_not_import_is_a_few_lines_not_a_traceback(
    tmp_path, command, source, where, why
):
    (tmp_path / "app.py").write_text(source)

    result = _invoke(tmp_path, *command)

    assert result.exit_code == 1
    assert "Importing 'app' failed" in result.output
    assert where in result.output
    assert why in result.output
    assert "Traceback" not in result.output
    assert result.exception is None or isinstance(result.exception, SystemExit)


def test_an_error_in_a_helper_is_reported_where_the_helper_raised(tmp_path):
    (tmp_path / "app.py").write_text(RAISING_HELPER)
    (tmp_path / "checkhelper.py").write_text("def go():\n    return 1 / 0\n\nX = go()\n")

    result = _invoke(tmp_path, "check")

    assert result.exit_code == 1
    assert "checkhelper.py:2, in go" in result.output
    assert "return 1 / 0" in result.output
    assert "ZeroDivisionError" in result.output


def test_check_refuses_an_app_a_run_would_refuse(tmp_path):
    """A port naming a structure no service of the app resolves: found without running."""
    (tmp_path / "app.py").write_text(
        "from arkitekt import App\n"
        "app = App('checked', '1.2.3')\n\n"
        "class Thing:\n"
        "    pass\n\n"
        "@app.action\n"
        "def take(thing: Thing) -> int:\n"
        "    return 1\n"
    )

    result = _invoke(tmp_path, "check")

    assert result.exit_code == 1
    assert "Thing" in result.output
