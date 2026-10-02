"""`arkitekt login`, `logout`, `status` and `self sessions`: the saved logins.

The first three see the app in the folder; `self sessions` sees the machine.
Nothing reaches a server: fakts is the offline one, and sessions are files in a
private state directory.
"""

import os
import time

import pytest
from typer.testing import CliRunner

from arkitekt.app.sessions import list_sessions, session_path
from arkitekt.cli.main import cli_app
from arkitekt.constants import DEFAULT_ARKITEKT_URL

from ..fakes import write_session

DAY = 86400
APP = ("com.test.app", "0.0.1")


@pytest.fixture
def saved(app_dir):
    """Save a session for the scaffolded app, as a run of it would have."""
    from arkitekt import runtime
    from arkitekt.cli.target import load_target

    app, _, _ = load_target("app", str(app_dir))
    approved = runtime.run_manifest(app).hash()

    def save(url=DEFAULT_ARKITEKT_URL, **kwargs):
        return write_session(*APP, url, manifest_hash=approved, **kwargs)

    return save


@pytest.fixture(autouse=True)
def _default_server(monkeypatch):
    monkeypatch.delenv("FAKTS_URL", raising=False)


def _invoke(work_dir, *args, **kwargs):
    return CliRunner().invoke(cli_app, ["--work-dir", str(work_dir), *args], **kwargs)


def _flat(output: str) -> str:
    """The output on one line: a status line wraps at the terminal's width."""
    return " ".join(output.split())


# --------------------------------------------------------------------------- #
# status
# --------------------------------------------------------------------------- #


def test_status_of_an_app_that_never_logged_in(app_dir):
    result = _invoke(app_dir, "status")

    assert result.exit_code == 0, result.output
    assert "com.test.app 0.0.1" in result.output
    assert "Not logged in" in result.output
    assert "arkitekt login" in result.output


def test_status_says_since_when_and_where(app_dir, saved):
    saved(logged_in_at=time.time() - 3 * DAY)

    result = _invoke(app_dir, "status")

    assert "Logged in" in result.output
    assert "3 days ago" in result.output and "Lab" in result.output
    assert "SECRET" not in result.output


def test_status_is_about_the_server_asked_for(app_dir, saved):
    saved()

    result = _invoke(app_dir, "status", "--url", "http://localhost:8000")

    assert "Not logged in" in result.output


def test_status_says_when_the_saved_session_is_too_old(app_dir, saved):
    saved(refreshed_at=time.time() - 60 * DAY)

    result = _invoke(app_dir, "status")

    assert "The saved session is idle" in _flat(result.output)
    assert "arkitekt login --reauth" in _flat(result.output)


def test_status_does_not_claim_a_session_the_run_would_not_use(app_dir):
    """Saved for the app as it was declared then: the run sends another manifest."""
    write_session(*APP, DEFAULT_ARKITEKT_URL, manifest_hash="f" * 64)

    result = _invoke(app_dir, "status")

    assert "another declaration of this app" in _flat(result.output)
    assert "Logged in " not in result.output


# --------------------------------------------------------------------------- #
# logout
# --------------------------------------------------------------------------- #


def test_logout_forgets_this_apps_session_only(app_dir):
    mine = write_session(*APP, DEFAULT_ARKITEKT_URL)
    elsewhere = write_session(*APP, "http://localhost:8000")
    another = write_session("another-app", "1.0.0", DEFAULT_ARKITEKT_URL)

    result = _invoke(app_dir, "logout")

    assert result.exit_code == 0, result.output
    assert "Logged out" in result.output
    # It does not claim more than it did.
    assert "Not revoked on the server" in _flat(result.output)
    assert not os.path.exists(mine)
    assert os.path.exists(elsewhere) and os.path.exists(another)


def test_logout_without_a_session_says_so(app_dir):
    result = _invoke(app_dir, "logout")

    assert result.exit_code == 0, result.output
    assert "Not logged in" in result.output


# --------------------------------------------------------------------------- #
# login
# --------------------------------------------------------------------------- #


@pytest.fixture
def logins(monkeypatch):
    """Replace the login itself: records what it was asked, and saves a session."""
    asked = []

    async def fake_alogin(app, **options):
        from fakts.cache.file import CacheFile

        asked.append((app, options))
        path = write_session(app.identifier, app.version, options.get("url", DEFAULT_ARKITEKT_URL))
        with open(path, encoding="utf-8") as file:
            return CacheFile.model_validate_json(file.read()).fakts

    monkeypatch.setattr("arkitekt.runtime.alogin", fake_alogin)
    return asked


def test_login_logs_in_and_saves_the_session(app_dir, logins):
    result = _invoke(app_dir, "login", "--headless")

    assert result.exit_code == 0, result.output
    ((app, options),) = logins
    assert app.identifier == "com.test.app"
    # Only what was passed, and always a fresh login: it was asked for by name.
    assert options == {"headless": True, "reauth": True}
    assert os.path.exists(session_path(*APP, DEFAULT_ARKITEKT_URL))


def test_login_leaves_a_good_session_alone(app_dir, logins, saved):
    saved(logged_in_at=time.time() - DAY)

    result = _invoke(app_dir, "login")

    assert result.exit_code == 0, result.output
    assert "Already logged in" in result.output
    assert logins == []


def test_login_reauth_replaces_a_good_session(app_dir, logins, saved):
    saved()

    result = _invoke(app_dir, "login", "--reauth")

    assert result.exit_code == 0, result.output
    assert len(logins) == 1


def test_login_replaces_a_session_that_is_too_old(app_dir, logins, saved):
    saved(refreshed_at=time.time() - 60 * DAY)

    result = _invoke(app_dir, "login")

    assert result.exit_code == 0, result.output
    assert len(logins) == 1


def test_login_replaces_a_session_the_run_would_not_use(app_dir, logins):
    write_session(*APP, DEFAULT_ARKITEKT_URL, manifest_hash="f" * 64)

    result = _invoke(app_dir, "login")

    assert result.exit_code == 0, result.output
    assert "Already logged in" not in result.output
    assert len(logins) == 1


def test_login_with_a_token_says_it_logged_in(app_dir, logins):
    result = _invoke(app_dir, "login", "--token", "client:refresh")

    assert "Logged in to Lab" in result.output
    assert "client:refresh" not in result.output and "SECRET" not in result.output


def test_a_declined_login_is_one_line(app_dir, monkeypatch):
    from fakts.grants.remote.errors import UserDeniedError

    async def declined(app, **options):
        raise UserDeniedError("denied")

    monkeypatch.setattr("arkitekt.runtime.alogin", declined)

    result = _invoke(app_dir, "login")

    assert result.exit_code == 1
    assert "The login was declined" in result.output
    assert "Traceback" not in result.output


def test_a_login_is_for_the_manifest_the_run_sends(app_dir, monkeypatch):
    """Else the run would not find the session `login` saved, and ask again.

    The app offers actions, so its run is rekuest's and requires what rekuest
    does: the manifest a bare connection would send lacks those requirements.
    """
    pytest.importorskip("rekuest")
    from fakts.testing import build_testing_fakts

    from arkitekt import connect, runtime
    from arkitekt.cli.target import load_target

    sent = []

    def recording(manifest, options):
        sent.append(manifest.hash())
        return build_testing_fakts(aliases={r.key: f"http://{r.key}.test" for r in manifest.requirements})

    monkeypatch.setattr("arkitekt.runtime.build_fakts", recording)

    result = _invoke(app_dir, "login", "--token", "client:refresh")

    assert result.exit_code == 0, result.output
    app, _, _ = load_target("app", str(app_dir))
    assert sent == [connect(app, provide=True)._prepare().manifest.hash()]
    assert sent != [connect(app)._prepare().manifest.hash()]
    assert sent == [runtime.run_manifest(app).hash()]


def test_logging_in_for_real_goes_through_fakts_and_nothing_else(app_dir):
    """The real `alogin`, on the offline fakts: no client is built, no agent."""
    result = _invoke(app_dir, "login", "--token", "client:refresh")

    assert result.exit_code == 0, result.output
    assert "Logged in to" in result.output


# --------------------------------------------------------------------------- #
# self sessions
# --------------------------------------------------------------------------- #


def test_self_sessions_lists_every_login_on_the_machine(tmp_path):
    write_session("my-app", "0.1.0", DEFAULT_ARKITEKT_URL, logged_in_at=time.time() - 2 * DAY)
    write_session("other-app", "1.0.0", "http://localhost:8000")

    result = _invoke(tmp_path, "self", "sessions")

    assert result.exit_code == 0, result.output
    assert "my-app-0.1.0" in result.output and "2 days ago" in result.output
    assert "other-app-1.0.0" in result.output and "http://localhost:8000" in result.output
    assert "SECRET" not in result.output


def test_self_sessions_with_nothing_saved(tmp_path):
    result = _invoke(tmp_path, "self", "sessions")

    assert result.exit_code == 0, result.output
    assert "No sessions on this machine" in result.output


def test_self_sessions_forgets_an_app_on_every_server(tmp_path):
    write_session("my-app", "0.1.0", DEFAULT_ARKITEKT_URL)
    write_session("my-app", "0.1.0", "http://localhost:8000")
    write_session("other-app", "1.0.0", DEFAULT_ARKITEKT_URL)

    result = _invoke(tmp_path, "self", "sessions", "--forget", "my-app-0.1.0")

    assert result.exit_code == 0, result.output
    assert "Forgot 2 sessions" in result.output
    assert [session.name for session in list_sessions()] == ["other-app-1.0.0"]


def test_self_sessions_asks_before_forgetting_everything(tmp_path):
    write_session("my-app", "0.1.0", DEFAULT_ARKITEKT_URL)

    declined = _invoke(tmp_path, "self", "sessions", "--all", input="n\n")
    assert declined.exit_code != 0
    assert len(list_sessions()) == 1

    result = _invoke(tmp_path, "self", "sessions", "--all", "--yes")
    assert result.exit_code == 0, result.output
    assert list_sessions() == []
