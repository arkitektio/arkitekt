"""`arkitekt check`, and what any command says when the app does not import."""

from pathlib import Path
from typing import Any

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


RUNS_AT_IMPORT = VALID + "\nfrom arkitekt import run\nrun(app)\n"

CONNECTS_AT_IMPORT = (
    VALID + "\nfrom arkitekt import connect\n"
    "with connect(app) as rt:\n"
    "    print(rt)\n"
)

EASY_AT_IMPORT = (
    VALID + "\nfrom arkitekt import easy\n"
    "with easy('checked') as rt:\n"
    "    print(rt)\n"
)


@pytest.fixture
def no_server(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every real way to a server raises: a check that reached one fails loudly."""

    def never(*args: object, **kwargs: object) -> None:
        raise AssertionError("check reached a server")

    async def anever(*args: object, **kwargs: object) -> None:
        raise AssertionError("check reached a server")

    monkeypatch.setattr("arkitekt.runtime.build_fakts", never)
    monkeypatch.setattr("arkitekt.runtime.Runtime.arun", anever)


def test_check_imports_an_app_that_runs_at_import_without_running_it(tmp_path: Path, no_server: None) -> None:
    (tmp_path / "app.py").write_text(RUNS_AT_IMPORT)

    result = _invoke(tmp_path, "check")

    assert result.exit_code == 0, result.output
    assert "checked 1.2.3 is valid" in result.output


@pytest.mark.parametrize("source", [CONNECTS_AT_IMPORT, EASY_AT_IMPORT], ids=["connect", "easy"])
def test_check_refuses_an_app_that_connects_at_import(tmp_path: Path, no_server: None, source: str) -> None:
    (tmp_path / "app.py").write_text(source)

    result = _invoke(tmp_path, "check")

    assert result.exit_code == 1
    said = " ".join(result.output.split())
    assert "app.py:9" in said and "connects" in said and "__main__" in said


def test_the_stubs_are_gone_after_the_check(tmp_path: Path, no_server: None) -> None:
    import arkitekt
    import arkitekt.runtime

    before = (arkitekt.run, arkitekt.runtime.run, arkitekt.runtime.Runtime.__dict__.get("__enter__"))
    (tmp_path / "app.py").write_text(RUNS_AT_IMPORT)

    assert _invoke(tmp_path, "check").exit_code == 0
    assert (arkitekt.run, arkitekt.runtime.run, arkitekt.runtime.Runtime.__dict__.get("__enter__")) == before


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


def test_check_lists_what_a_blok_uses_that_its_catalog_does_not_know(tmp_path):
    """A catalog finding does not block a run, so check says it and still passes."""
    (tmp_path / "app.py").write_text(
        VALID + "\napp.blok('panel', '<Html><Card><Slidr /><Button lable=\"Go\" /></Card></Html>')\n"
    )

    result = _invoke(tmp_path, "check")

    assert result.exit_code == 0, result.output
    said = " ".join(result.output.split())  # the console wraps long lines
    assert "<Slidr>" in said and "[catalog.unknown_component]" in said
    assert "'lable'" in said and "[catalog.props]" in said
    assert "2 warnings" in said


def test_check_refuses_a_strict_blok_its_catalog_does_not_know(tmp_path):
    (tmp_path / "app.py").write_text(
        VALID + "\napp.blok('panel', '<Html><Card><Slidr /></Card></Html>', mode='strict')\n"
    )

    result = _invoke(tmp_path, "check")

    assert result.exit_code == 1
    assert "[catalog.unknown_component]" in " ".join(result.output.split())


def _report(work_dir: Path, *args: str) -> tuple[int, Any]:
    import json

    out = work_dir / "report.json"
    result = _invoke(work_dir, "check", "--json-out", str(out), *args)
    return result.exit_code, json.loads(out.read_text())


def _line_of(source: str, text: str) -> int:
    return next(number for number, line in enumerate(source.splitlines(), start=1) if text in line)


MULTILINE_BLOK = VALID + '\napp.blok(\n    "panel",\n    """\n    <Html><Card><Slidr /></Card></Html>\n    """,\n)\n'


def test_check_json_out_places_each_warning_at_its_blok(tmp_path: Path) -> None:
    """The report says which blok, which node and which declaring line: what an editor underlines."""
    (tmp_path / "app.py").write_text(MULTILINE_BLOK)

    code, report = _report(tmp_path)

    assert code == 0
    assert report["version"] == 1 and report["ok"] is True
    assert report["app"] == {"identifier": "checked", "version": "1.2.3"}
    (diagnostic,) = report["diagnostics"]
    assert diagnostic["code"] == "catalog.unknown_component" and diagnostic["level"] == "warning"
    assert diagnostic["blok"] == "panel" and "Slidr" in diagnostic["node"]
    assert diagnostic["file"] == str(tmp_path / "app.py")
    assert diagnostic["call_line"] == _line_of(MULTILINE_BLOK, "app.blok(")
    (blok,) = report["bloks"]
    assert blok["blok"] == "panel" and blok["context"] == "HTML"
    assert blok["source"] in MULTILINE_BLOK, "the source as written: an editor finds the literal by it"
    assert blok["call_line"] == diagnostic["call_line"]


def test_check_json_out_names_an_action_blok_by_interface_and_context(tmp_path: Path) -> None:
    source = (
        "from arkitekt import App\n"
        "app = App('checked', '1.2.3')\n\n"
        "@app.workflow(bloks='<Html><Card><Slidr /><ask /></Card></Html>')\n"
        "def add(a: int) -> int:\n"
        "    return a\n"
    )
    (tmp_path / "app.py").write_text(source)

    code, report = _report(tmp_path)

    assert code == 0
    assert {d["blok"] for d in report["diagnostics"]} == {"add:html"}
    assert [blok["blok"] for blok in report["bloks"]] == ["add:html"]


def test_check_json_out_records_the_refusal_that_stopped_it(tmp_path: Path) -> None:
    source = VALID + "\napp.blok('panel', '<Html><Card><Slidr /></Card></Html>', mode='strict')\n"
    (tmp_path / "app.py").write_text(source)

    code, report = _report(tmp_path)

    assert code == 1
    assert report["ok"] is False and report["bloks"] == []
    (error,) = report["diagnostics"]
    assert error["level"] == "error" and error["code"] == "catalog.unknown_component"
    assert "Slidr" in error["node"]
    assert (error["file"], error["call_line"]) == (str(tmp_path / "app.py"), _line_of(source, "app.blok("))


def test_check_json_out_places_a_parse_error_in_the_bsx(tmp_path: Path) -> None:
    source = VALID + "\napp.blok('panel', '<Html><Card></Html>')\n"
    (tmp_path / "app.py").write_text(source)

    code, report = _report(tmp_path)

    assert code == 1
    (error,) = report["diagnostics"]
    assert error["code"] and error["line"] == 1 and error["column"] >= 1
    assert error["call_line"] == _line_of(source, "app.blok(")


def test_check_json_out_records_an_app_that_does_not_import(tmp_path: Path) -> None:
    (tmp_path / "app.py").write_text(UNCLOSED)

    code, report = _report(tmp_path)

    assert code == 1
    assert report["app"] is None
    (error,) = report["diagnostics"]
    assert error["message"].startswith("SyntaxError") and error["file"] == str(tmp_path / "app.py")


def test_check_json_out_is_not_corrupted_by_what_the_app_prints(tmp_path: Path) -> None:
    (tmp_path / "app.py").write_text("print('{not json')\n" + VALID)

    code, report = _report(tmp_path)

    assert code == 0 and report["ok"] is True
