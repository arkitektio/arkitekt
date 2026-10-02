"""The saved sessions: where they live, what they say, and that they keep their secrets."""

import os
import time

from arkitekt.app import sessions
from arkitekt.app.sessions import forget, list_sessions, read_session, session_path
from fakts.session import REFRESH_CHAIN_MAX_AGE, REFRESH_TOKEN_MAX_AGE

from .fakes import write_session

LAB = "https://lab.example"
DAY = 86400


def test_a_session_says_where_and_when_it_was_logged_in() -> None:
    then = time.time() - 3 * DAY
    path = write_session("my-app", "0.1.0", LAB, logged_in_at=then)

    session = read_session(path)

    assert session is not None
    assert (session.name, session.url, session.deployment) == ("my-app-0.1.0", LAB, "Lab")
    assert session.logged_in_at == then
    assert session.state() == "active"


def test_a_session_is_for_the_manifest_it_was_approved_with() -> None:
    session = read_session(write_session("my-app", "0.1.0", LAB, manifest_hash="a" * 64))

    assert session is not None
    assert session.is_for("a" * 64)
    assert not session.is_for("b" * 64)


def test_a_session_keeps_its_tokens_to_itself() -> None:
    session = read_session(write_session("my-app", "0.1.0", LAB))

    assert "SECRET" not in repr(session)


def test_a_session_unused_for_too_long_is_idle_and_one_too_old_is_expired() -> None:
    now = time.time()
    idle = write_session("idle", "1", LAB, refreshed_at=now - REFRESH_TOKEN_MAX_AGE - DAY)
    old = write_session("old", "1", LAB, logged_in_at=now - REFRESH_CHAIN_MAX_AGE - DAY)

    idle_session, old_session = read_session(idle), read_session(old)
    assert idle_session is not None and old_session is not None
    assert idle_session.state() == "idle"
    assert old_session.state() == "expired"


def test_no_session_and_an_unreadable_one_are_both_none(tmp_path) -> None:
    broken = tmp_path / "broken_fakts_cache.json"
    broken.write_text("{not json")

    assert read_session(str(tmp_path / "missing_fakts_cache.json")) is None
    assert read_session(str(broken)) is None


def test_one_app_on_two_servers_has_two_sessions() -> None:
    assert session_path("app", "1", LAB) != session_path("app", "1", "http://localhost:8000")


def test_listing_shows_only_our_sessions() -> None:
    """Other clients keep their files beside ours: they are not listed, nor removed."""
    path = write_session("my-app", "0.1.0", LAB)
    write_session("other-app", "2.0.0-rc1", LAB)
    beside = [path + ".lock", path.replace(".json", ".rs.json"), path + ".1.abc.tmp"]
    for name in beside:
        with open(name, "w") as file:
            file.write("{}")

    assert [session.name for session in list_sessions()] == ["my-app-0.1.0", "other-app-2.0.0-rc1"]

    assert forget(path) is True
    assert forget(path) is False
    assert all(os.path.exists(name) for name in beside)


def test_listing_before_anything_was_saved_is_empty() -> None:
    assert not os.path.exists(sessions.cache_dir())
    assert list_sessions() == []
