"""How the CLI looks: the mark, the banner beside it, and the status lines."""

import io

from rich.console import Console
from typer.testing import CliRunner

from arkitekt import App
from arkitekt.app.fakts import resolve_url
from arkitekt.cli import ui
from arkitekt.cli.main import cli_app
from arkitekt.cli.texts import ASCII_MARK, MARK
from arkitekt.constants import DEFAULT_ARKITEKT_URL


def _console(encoding: str = "utf-8") -> tuple[Console, io.BytesIO]:
    raw = io.BytesIO()
    # newline="": what the console writes is what is read back, on Windows too.
    stream = io.TextIOWrapper(raw, encoding=encoding, write_through=True, newline="")
    return Console(file=stream, width=80, color_system=None), raw


def _written(raw: io.BytesIO, encoding: str = "utf-8") -> str:
    return raw.getvalue().decode(encoding)


def test_the_root_help_shows_the_mark_on_three_rows():
    result = CliRunner().invoke(cli_app, ["--help"])

    assert result.exit_code == 0, result.output
    rows = [line.strip() for line in result.output.splitlines()]
    for row in MARK:
        assert any(line.startswith(row) for line in rows), result.output
    assert sum(line.startswith("■") for line in rows) == 3


def test_the_banner_puts_its_lines_beside_the_mark():
    console, raw = _console()

    console.print(ui.Banner("one", "two", "three"))

    lines = _written(raw).splitlines()
    assert [line.split()[0] for line in lines] == list(MARK)
    assert [line.split()[-1] for line in lines] == ["one", "two", "three"]
    # One column: the text starts at the same cell on every row.
    assert len({line.index(word) for line, word in zip(lines, ("one", "two", "three"))}) == 1


def test_a_terminal_that_cannot_encode_the_mark_gets_the_ascii_one():
    console, raw = _console(encoding="ascii")

    console.print(ui.Banner("one"))
    ui.step(console, "building")
    ui.done(console, "built")
    ui.notice(console, "waiting")
    ui.fail(console, "broke")

    written = _written(raw)
    for row in ASCII_MARK:
        assert row in written
    assert written.splitlines()[3:] == ["# building", "* built", "- waiting", "x broke"]


def test_a_run_banner_survives_an_ascii_stream():
    app = App("com.test.app", "0.0.1", author="tester")
    console, raw = _console(encoding="ascii")

    console.print(ui.construct_app_banner(app, "http://fakts.example"))

    written = _written(raw, "ascii")
    assert "com.test.app 0.0.1 - tester" in written
    assert "connecting to http://fakts.example" in written


def test_a_status_line_leads_with_its_glyph_and_trails_its_detail():
    console, raw = _console()

    ui.done(console, "Built flavour vanilla", "build 42")

    assert _written(raw) == "◆ Built flavour vanilla  build 42\n"


def test_the_shown_url_is_the_one_the_run_connects_to(monkeypatch):
    monkeypatch.delenv("FAKTS_URL", raising=False)
    assert resolve_url(None) == DEFAULT_ARKITEKT_URL

    monkeypatch.setenv("FAKTS_URL", "http://env.example")
    assert resolve_url(None) == "http://env.example"
    assert resolve_url("http://passed.example") == "http://passed.example"
