"""`arkitekt check`, and what any command says when the app does not import."""

from pathlib import Path
from typing import Any, Never

import pytest
from typer.testing import CliRunner, Result

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

RAISING_HELPER = (
    "from arkitekt import App\nimport checkhelper\napp = App('checked', '1.2.3')\n"
)


def _invoke(work_dir: Path, *args: str) -> Result:
    return CliRunner().invoke(cli_app, ["--work-dir", str(work_dir), *args])


def test_check_says_what_a_valid_app_declares(tmp_path: Path) -> None:
    (tmp_path / "app.py").write_text(VALID)

    result = _invoke(tmp_path, "check")

    assert result.exit_code == 0, result.output
    assert "checked 1.2.3 is valid" in result.output
    assert "1 action" in result.output


def test_check_connects_to_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def never(*args: object, **kwargs: object) -> Never:
        raise AssertionError("check connected")

    monkeypatch.setattr("arkitekt.runtime.connect", never)
    monkeypatch.setattr("arkitekt.runtime.build_fakts", never)
    (tmp_path / "app.py").write_text(VALID)

    assert _invoke(tmp_path, "check").exit_code == 0


RUNS_AT_IMPORT = VALID + "\nfrom arkitekt import run\nrun(app)\n"

CONNECTS_AT_IMPORT = (
    VALID + "\nfrom arkitekt import connect\nwith connect(app) as rt:\n    print(rt)\n"
)

# A script's ``connect(Client)``; the ``with`` is on line 9 here too.
CLIENTS_AT_IMPORT = VALID + (
    "from arkitekt import connect\nfrom tests.fakes import PictureClient\n"
    "with connect(PictureClient) as pictures:\n    print(pictures)\n"
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


def test_check_imports_an_app_that_runs_at_import_without_running_it(
    tmp_path: Path, no_server: None
) -> None:
    (tmp_path / "app.py").write_text(RUNS_AT_IMPORT)

    result = _invoke(tmp_path, "check")

    assert result.exit_code == 0, result.output
    assert "checked 1.2.3 is valid" in result.output


@pytest.mark.parametrize(
    "source", [CONNECTS_AT_IMPORT, CLIENTS_AT_IMPORT], ids=["app", "clients"]
)
def test_check_refuses_an_app_that_connects_at_import(
    tmp_path: Path, no_server: None, source: str
) -> None:
    (tmp_path / "app.py").write_text(source)

    result = _invoke(tmp_path, "check")

    assert result.exit_code == 1
    said = " ".join(result.output.split())
    assert "app.py:9" in said and "connects" in said and "__main__" in said


def test_the_stubs_are_gone_after_the_check(tmp_path: Path, no_server: None) -> None:
    import arkitekt
    import arkitekt.runtime

    before = (
        arkitekt.run,
        arkitekt.runtime.run,
        arkitekt.runtime.Runtime.__dict__.get("__enter__"),
    )
    (tmp_path / "app.py").write_text(RUNS_AT_IMPORT)

    assert _invoke(tmp_path, "check").exit_code == 0
    assert (
        arkitekt.run,
        arkitekt.runtime.run,
        arkitekt.runtime.Runtime.__dict__.get("__enter__"),
    ) == before


@pytest.mark.parametrize(
    "command", [["check"], ["run", "prod"], ["inspect", "all"], ["status"]]
)
@pytest.mark.parametrize(
    ("source", "where", "why", "header"),
    [
        # Imports fine; assembling it finds the port it cannot build, at its line.
        (UNTYPED, "app.py:4", "type hint for a", "is not valid"),
        (UNCLOSED, "app.py:2", "never closed", "Importing 'app' failed"),
    ],
)
def test_an_app_that_does_not_import_is_a_few_lines_not_a_traceback(
    tmp_path: Path, command: list[str], source: str, where: str, why: str, header: str
) -> None:
    (tmp_path / "app.py").write_text(source)

    result = _invoke(tmp_path, *command)

    assert result.exit_code == 1
    assert header in result.output
    assert where in result.output
    assert why in result.output
    assert "Traceback" not in result.output
    assert result.exception is None or isinstance(result.exception, SystemExit)


def test_an_error_in_a_helper_is_reported_where_the_helper_raised(
    tmp_path: Path,
) -> None:
    (tmp_path / "app.py").write_text(RAISING_HELPER)
    (tmp_path / "checkhelper.py").write_text(
        "def go():\n    return 1 / 0\n\nX = go()\n"
    )

    result = _invoke(tmp_path, "check")

    assert result.exit_code == 1
    assert "checkhelper.py:2, in go" in result.output
    assert "return 1 / 0" in result.output
    assert "ZeroDivisionError" in result.output


def test_check_refuses_an_app_a_run_would_refuse(tmp_path: Path) -> None:
    """A port naming a class nothing declares: found without running."""
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


def test_check_lists_what_a_blok_uses_that_its_catalog_does_not_know(
    tmp_path: Path,
) -> None:
    """A catalog finding does not block a run, so check says it and still passes."""
    (tmp_path / "app.py").write_text(
        VALID
        + '\napp.blok(\'panel\', \'<Blok kind="agent" context="panel"><Card><Slidr /><Button lable="Go" /></Card></Blok>\')\n'
    )

    result = _invoke(tmp_path, "check")

    assert result.exit_code == 0, result.output
    said = " ".join(result.output.split())  # the console wraps long lines
    assert "<Slidr>" in said and "[catalog.unknown_component]" in said
    assert "'lable'" in said and "[catalog.props]" in said
    assert "2 warnings" in said


def test_check_refuses_a_strict_blok_its_catalog_does_not_know(tmp_path: Path) -> None:
    (tmp_path / "app.py").write_text(
        VALID
        + "\napp.blok('panel', '<Blok kind=\"agent\" context=\"panel\"><Card><Slidr /></Card></Blok>', mode='strict')\n"
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
    return next(
        number
        for number, line in enumerate(source.splitlines(), start=1)
        if text in line
    )


MULTILINE_BLOK = (
    VALID
    + '\napp.blok(\n    "panel",\n    """\n    <Blok kind="agent" context="panel"><Card><Slidr /></Card></Blok>\n    """,\n)\n'
)


def test_check_json_out_places_each_warning_at_its_blok(tmp_path: Path) -> None:
    """The report says which blok, which node and which declaring line: what an editor underlines."""
    (tmp_path / "app.py").write_text(MULTILINE_BLOK)

    code, report = _report(tmp_path)

    assert code == 0
    assert report["version"] == 4 and report["ok"] is True
    assert report["app"] == {"identifier": "checked", "version": "1.2.3"}
    (diagnostic,) = report["diagnostics"]
    assert (
        diagnostic["code"] == "catalog.unknown_component"
        and diagnostic["level"] == "warning"
    )
    assert diagnostic["blok"] == "panel" and "Slidr" in diagnostic["node"]
    assert diagnostic["file"] == str(tmp_path / "app.py")
    assert diagnostic["call_line"] == _line_of(MULTILINE_BLOK, "app.blok(")
    (blok,) = report["bloks"]
    assert blok["blok"] == "panel" and blok["context"] == "PANEL"
    assert blok["source"] in MULTILINE_BLOK, (
        "the source as written: an editor finds the literal by it"
    )
    assert blok["call_line"] == diagnostic["call_line"]
    assert blok["scope"]["kinds"] == ["agent"], (
        "where it is mounted: app.blok takes an agent blok"
    )
    assert blok["scope"]["args"] == [], "an app blok declaring no args reads none"


def test_check_json_out_names_an_action_blok_by_interface_and_context(
    tmp_path: Path,
) -> None:
    source = (
        "from arkitekt import App\n"
        "app = App('checked', '1.2.3')\n\n"
        '@app.workflow(bloks=\'<Blok kind="action" context="panel"><Card><Slidr /><ask /></Card></Blok>\')\n'
        "def add(a: int) -> int:\n"
        "    return a\n"
    )
    (tmp_path / "app.py").write_text(source)

    code, report = _report(tmp_path)

    assert code == 0
    assert {d["blok"] for d in report["diagnostics"]} == {"add:panel"}
    (blok,) = report["bloks"]
    assert blok["blok"] == "add:panel"
    assert (blok["file"], blok["call_line"]) == (
        str(tmp_path / "app.py"),
        _line_of(source, "@app.workflow"),
    )
    assert blok["scope"]["kinds"] == ["action", "assign"] and blok["scope"]["args"] == [
        "a"
    ]


DEPENDENT = (
    "from typing import Protocol\n"
    "from arkitekt import App\n"
    "app = App('checked', '1.2.3')\n\n"
    "@app.declare(app='lab')\n"
    "class Lab(Protocol):\n"
    "    def ping(self, n: int) -> int:\n"
    '        """Ping."""\n'
    "        ...\n\n"
    '@app.workflow(bloks=\'<Blok kind="action" context="panel"><Card /></Blok>\')\n'
    "def run(lab: Lab, a: int) -> int:\n"
    "    return a\n"
)


def test_check_json_out_lists_the_protocols_and_who_takes_them(tmp_path: Path) -> None:
    """What an editor asks a server about: each protocol, its dependency and the parameters that take it."""
    (tmp_path / "app.py").write_text(DEPENDENT)

    code, report = _report(tmp_path)

    assert code == 0, report["diagnostics"]
    (protocol,) = report["protocols"]
    assert protocol["name"] == "Lab" and protocol["file"] == str(tmp_path / "app.py")
    assert protocol["line"] == _line_of(DEPENDENT, "@app.declare")
    assert protocol["dependency"]["app"] == "lab"
    assert [
        action["key"] for action in protocol["dependency"]["action_dependencies"]
    ] == ["ping"]
    assert protocol["used_by"] == [{"action": "run", "key": "lab"}]
    (blok,) = report["bloks"]
    assert [dependency["key"] for dependency in blok["scope"]["dependencies"]] == [
        "lab"
    ]


def test_check_json_out_names_the_class_behind_each_identifier(tmp_path: Path) -> None:
    """What an editor needs to write a port's type: the identifier's class, and where to import it."""
    (tmp_path / "shapes.py").write_text("class Cell:\n    id: str\n")
    (tmp_path / "app.py").write_text(
        "from arkitekt import App\nfrom shapes import Cell\n"
        "app = App('checked', '1.2.3')\n"
        "async def expand(id: str) -> Cell:\n"
        "    return Cell()\n"
        "app.register_structure(Cell, '@t/cell', expand=expand)\n"
    )

    code, report = _report(tmp_path)

    assert code == 0, report["diagnostics"]
    cell = next(
        record for record in report["structures"] if record["identifier"] == "@t/cell"
    )
    assert (cell["kind"], cell["name"], cell["module"]) == (
        "STRUCTURE",
        "Cell",
        "shapes",
    )
    assert cell["file"] == str(tmp_path / "shapes.py")


def test_check_json_out_records_the_refusal_that_stopped_it(tmp_path: Path) -> None:
    source = (
        VALID
        + "\napp.blok('panel', '<Blok kind=\"agent\" context=\"panel\"><Card><Slidr /></Card></Blok>', mode='strict')\n"
    )
    (tmp_path / "app.py").write_text(source)

    code, report = _report(tmp_path)

    assert code == 1
    assert report["ok"] is False and report["bloks"] == []
    (error,) = report["diagnostics"]
    assert error["level"] == "error" and error["code"] == "catalog.unknown_component"
    assert "Slidr" in error["node"]
    assert (error["file"], error["call_line"]) == (
        str(tmp_path / "app.py"),
        _line_of(source, "app.blok("),
    )


def test_check_json_out_places_a_parse_error_in_the_bsx(tmp_path: Path) -> None:
    source = (
        VALID
        + "\napp.blok('panel', '<Blok kind=\"agent\" context=\"panel\"><Card></Blok>')\n"
    )
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
    assert error["message"].startswith("SyntaxError") and error["file"] == str(
        tmp_path / "app.py"
    )


def test_check_json_out_is_not_corrupted_by_what_the_app_prints(tmp_path: Path) -> None:
    (tmp_path / "app.py").write_text("print('{not json')\n" + VALID)

    code, report = _report(tmp_path)

    assert code == 0 and report["ok"] is True


def test_check_json_out_lists_actions_by_hash_and_states_by_class(
    tmp_path: Path,
) -> None:
    import json

    (tmp_path / "app.py").write_text(
        VALID + "\nfrom dataclasses import dataclass\n\n"
        "@app.state(name='counter')\n@dataclass\nclass Counter:\n    count: int = 0\n"
    )
    out = tmp_path / "report.json"

    assert _invoke(tmp_path, "check", "--json-out", str(out)).exit_code == 0

    report = json.loads(out.read_text())
    (action, *_) = report["actions"]
    assert action["hash"] and action["line"] and action["file"].endswith("app.py")
    # What an editor follows self.counter to.
    (state,) = report["states"]
    assert state["key"] == "counter" and state["name"] == "Counter"
    assert state["file"].endswith("app.py")


def test_check_json_prints_the_report_alone_on_stdout(tmp_path: Path) -> None:
    """What the app prints while it is imported, and the status line, go to stderr."""
    import json

    (tmp_path / "app.py").write_text("print('hello from the app')\n" + VALID)

    result = _invoke(tmp_path, "check", "--json")

    assert result.exit_code == 0, result.output
    report = json.loads(result.stdout)
    assert report["ok"] is True and report["app"] == {
        "identifier": "checked",
        "version": "1.2.3",
    }
    assert [action["interface"] for action in report["actions"]] == ["add"]
    assert "hello from the app" in result.stderr


def test_check_json_reports_a_refusal_and_fails(tmp_path: Path) -> None:
    import json

    (tmp_path / "app.py").write_text(UNTYPED)

    result = _invoke(tmp_path, "check", "--json")

    assert result.exit_code == 1
    report = json.loads(result.stdout)
    assert report["ok"] is False and report["diagnostics"]


ROBOT = (
    "from arkitekt import App\n"
    "app = App('robot', '1.0.0')\n\n"
    "@app.action\n"
    "def move(trajectory: str) -> bool:\n"
    "    return True\n"
)

LAB = (
    "from arkitekt import App\n"
    "app = App('lab', '1.0.0')\n\n"
    "@app.declare(app='robot')\n"
    "class Robot:\n"
    "    def move(self, {argument}: str) -> bool: ...\n\n"
    "@app.workflow\n"
    "def go(robot: Robot) -> bool:\n"
    "    return robot.move('home')\n"
)


@pytest.mark.parametrize(("argument", "exit_code"), [("trajectory", 0), ("name", 1)])
def test_check_with_another_app_compares_what_is_demanded_of_it(
    tmp_path: Path, argument: str, exit_code: int
) -> None:
    (tmp_path / "robot.py").write_text(ROBOT)
    (tmp_path / "lab.py").write_text(LAB.format(argument=argument))

    result = _invoke(tmp_path, "check", "lab", "--with", "robot")

    assert result.exit_code == exit_code, result.output
    assert ("is expected at 0" in result.output) is bool(exit_code)


ASSIGN_BLOK = (
    VALID
    + "\nfrom arkitekt import ActionBlok\n\n\n@app.workflow(\n"
    + "    bloks=[\n"
    + '        ActionBlok(\'<Blok kind="action" context="panel"><Text>{task.status}</Text></Blok>\'),\n'
    + '        ActionBlok(\'<Blok kind="assign" context="panel"><args /><Button onClick={assign.start()}>Go</Button></Blok>\'),\n'
    + "    ],\n"
    + ')\ndef stain(rounds: int = 1) -> None:\n    """Stain\n\n    Stains a slide\n    """\n'
)


def test_an_assign_blok_is_reported_as_one(tmp_path: Path) -> None:
    """Its id says it is the action's assign blok; its `<Blok kind>` what an editor lets it read."""
    (tmp_path / "app.py").write_text(ASSIGN_BLOK)

    code, report = _report(tmp_path)

    assert code == 0, report["diagnostics"]
    assert [blok["blok"] for blok in report["bloks"]] == [
        "stain:panel",
        "stain:assign:panel",
    ]
