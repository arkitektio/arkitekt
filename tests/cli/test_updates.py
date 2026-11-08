"""Saying, once a command is done, that a newer arkitekt is out."""

import io
import json
import time
from pathlib import Path

import pytest
from rich.console import Console

from arkitekt.cli import updates
from arkitekt.cli.updates import CHECK_EVERY_SECONDS, UpdateCheck, is_newer, wanted


def _said(check: UpdateCheck) -> str:
    out = io.StringIO()
    check.finish(Console(file=out, width=200))
    return " ".join(out.getvalue().split())


def _settle(check: UpdateCheck) -> None:
    if check._thread is not None:  # noqa: SLF001
        check._thread.join(timeout=5)  # noqa: SLF001


def test_a_newer_release_is_said_with_how_to_get_it(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(updates, "fetch_latest", lambda: "13.7.0")
    monkeypatch.setattr(updates, "upgrade_hint", lambda work_dir: "uvx arkitekt@latest")
    check = UpdateCheck("13.6.0", cache_file=str(tmp_path / "latest.json"))
    _settle(check)

    said = _said(check)

    assert "arkitekt 13.7.0 is out (this is 13.6.0)" in said
    assert "`uvx arkitekt@latest`" in said
    assert json.loads((tmp_path / "latest.json").read_text())["latest"] == "13.7.0"


def test_the_running_release_says_nothing(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(updates, "fetch_latest", lambda: "13.6.0")
    check = UpdateCheck("13.6.0", cache_file=str(tmp_path / "latest.json"))
    _settle(check)

    assert _said(check) == ""


def test_pypi_is_asked_at_most_once_a_day(tmp_path: Path, monkeypatch) -> None:
    cache = tmp_path / "latest.json"
    cache.write_text(json.dumps({"latest": "14.0.0", "checked_at": time.time() - 60}))
    monkeypatch.setattr(updates, "fetch_latest", lambda: pytest.fail("asked again within a day"))

    check = UpdateCheck("13.6.0", cache_file=str(cache))

    assert check._thread is None  # noqa: SLF001
    assert "arkitekt 14.0.0 is out" in _said(check), "the kept answer is still said"


def test_a_day_old_answer_is_asked_again(tmp_path: Path, monkeypatch) -> None:
    cache = tmp_path / "latest.json"
    cache.write_text(json.dumps({"latest": "13.6.0", "checked_at": time.time() - CHECK_EVERY_SECONDS - 1}))
    monkeypatch.setattr(updates, "fetch_latest", lambda: "13.8.0")

    check = UpdateCheck("13.6.0", cache_file=str(cache))
    _settle(check)

    assert "arkitekt 13.8.0 is out" in _said(check)


def test_an_answer_that_is_not_in_holds_nothing_up(tmp_path: Path, monkeypatch) -> None:
    import threading

    release = threading.Event()

    def slow() -> str:
        release.wait(5)
        return "99.0.0"

    monkeypatch.setattr(updates, "fetch_latest", slow)
    check = UpdateCheck("13.6.0", cache_file=str(tmp_path / "latest.json"))

    started = time.monotonic()
    out = io.StringIO()
    check.finish(Console(file=out), wait=0.2)
    assert out.getvalue() == ""
    assert time.monotonic() - started < 1
    release.set()


def test_an_answer_that_comes_in_after_the_command_is_kept_for_the_next(tmp_path: Path, monkeypatch) -> None:
    import threading

    release = threading.Event()

    def slow() -> str:
        release.wait(5)
        return "13.9.0"

    monkeypatch.setattr(updates, "fetch_latest", slow)
    check = UpdateCheck("13.6.0", cache_file=str(tmp_path / "latest.json"))
    check.finish(Console(file=io.StringIO()), wait=0.05)
    release.set()
    _settle(check)

    assert json.loads((tmp_path / "latest.json").read_text())["latest"] == "13.9.0"


def test_pypi_out_of_reach_says_nothing(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(updates, "fetch_latest", lambda: None)
    check = UpdateCheck("13.6.0", cache_file=str(tmp_path / "latest.json"))
    _settle(check)

    assert _said(check) == ""
    assert not (tmp_path / "latest.json").exists()


@pytest.mark.parametrize(
    ("latest", "current", "newer"),
    [
        ("13.6.3", "13.6.0", True),
        ("14.0.0", "13.9.9", True),
        ("13.6.0", "13.6.0", False),
        ("13.5.0", "13.6.0", False),
        ("junk", "13.6.0", False),
        # A source checkout is not a release to upgrade.
        ("13.6.3", "13.4.1.dev0+g569f36ecc.d20261107", False),
    ],
)
def test_releases_compare_by_pep_440(latest: str, current: str, newer: bool) -> None:
    assert is_newer(latest, current) is newer


class _Tty(io.StringIO):
    def isatty(self) -> bool:
        return True


def test_it_is_asked_only_where_someone_reads_it() -> None:
    assert wanted({}, _Tty()) is True
    assert wanted({}, io.StringIO()) is False, "stderr is not a terminal"
    assert wanted({"CI": "true"}, _Tty()) is False
    assert wanted({"ARKITEKT_NO_UPDATE_CHECK": "1"}, _Tty()) is False


def test_uvx_is_told_to_ask_for_latest(monkeypatch) -> None:
    monkeypatch.setattr("sys.prefix", "/home/me/.cache/uv/archive-v0/AbC123")
    assert updates.upgrade_hint(None) == "uvx arkitekt@latest"
