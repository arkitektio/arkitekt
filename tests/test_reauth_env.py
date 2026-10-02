"""reauth logs a run in again and caches the fresh session; skip_cache caches nothing.

The two used to be one flag (``no_cache``), so a "relogin" never stuck: the
next plain start found the old session again.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fakts.cache.file import FileCache
from fakts.cache.nocache import NoCache
from fakts.models import ActiveFakts, Manifest

import arkitekt.app.fakts as app_fakts
from arkitekt.app.fakts import ReauthCache, build_fakts, reauth_from_env
from arkitekt.app.options import ConnectionOptions

MANIFEST = Manifest(identifier="reauth-app", version="0.0.1", scopes=["openid"])
URL = "http://localhost:8000"


class MemoryCache:
    """A cache holding one value, standing in for a file with a session in it."""

    def __init__(self, value: object | None) -> None:
        self.value = value

    async def aload(self) -> object | None:
        return self.value

    async def aset(self, value: object) -> None:
        self.value = value

    async def areset(self) -> None:
        self.value = None


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    for name in ("ARKITEKT_REAUTH", "FAKTS_TOKEN", "FAKTS_REDEEM_TOKEN", "FAKTS_URL"):
        monkeypatch.delenv(name, raising=False)
    path = tmp_path / "cache" / "session.json"
    monkeypatch.setattr(app_fakts, "_cache_path", lambda manifest, url: str(path))


@pytest.mark.parametrize("value", ["1", "true", "YES", " on "])
def test_reauth_on(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    monkeypatch.setenv("ARKITEKT_REAUTH", value)
    assert reauth_from_env() is True


@pytest.mark.parametrize("value", ["", "0", "false", "off"])
def test_reauth_off(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    monkeypatch.setenv("ARKITEKT_REAUTH", value)
    assert reauth_from_env() is False


def test_a_typo_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ARKITEKT_REAUTH", "ture")
    with pytest.raises(ValueError, match="ARKITEKT_REAUTH"):
        reauth_from_env()


def test_a_plain_run_reads_and_writes_the_file() -> None:
    fakts = build_fakts(MANIFEST, ConnectionOptions(url=URL))
    assert isinstance(fakts.cache, FileCache)


def test_skip_cache_keeps_the_session_in_memory() -> None:
    fakts = build_fakts(MANIFEST, ConnectionOptions(url=URL, skip_cache=True, reauth=True))
    assert isinstance(fakts.cache, NoCache)


@pytest.mark.parametrize(
    "options",
    [
        ConnectionOptions(url=URL, reauth=True),
        ConnectionOptions(url=URL, reauth=True, token="client:refresh"),
        ConnectionOptions(url=URL, reauth=True, redeem_token="redeem-me"),
    ],
)
def test_reauth_still_caches_to_the_file(options: ConnectionOptions) -> None:
    fakts = build_fakts(MANIFEST, options)
    assert isinstance(fakts.cache, ReauthCache)
    assert isinstance(fakts.cache.cache, FileCache)


def test_the_environment_asks_for_reauth(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ARKITEKT_REAUTH", "1")
    fakts = build_fakts(MANIFEST, ConnectionOptions(url=URL))
    assert isinstance(fakts.cache, ReauthCache)


@pytest.mark.asyncio
async def test_reauth_hides_the_old_session_until_the_new_one_is_written() -> None:
    backing = MemoryCache("old session")
    cache = ReauthCache(cache=backing)  # pyright: ignore[reportArgumentType]

    # The start misses, so the grant runs; the old session is left in place
    # in case that login fails.
    assert await cache.aload() is None
    assert backing.value == "old session"

    new: ActiveFakts = "new session"  # pyright: ignore[reportAssignmentType]
    await cache.aset(new)
    assert backing.value == "new session"
    # From here fakts re-reads the cache mid-run (sibling rotations, stale-write
    # checks), and must see what is really there.
    assert await cache.aload() == "new session"
