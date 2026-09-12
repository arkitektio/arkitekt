"""The fakts session cache: where it lives and who can read it.

That file holds a live, rotating refresh token. It used to sit in a
`.arkitekt/cache/` directory created with a bare `os.makedirs`, which under
the umask 002 that Debian and Ubuntu ship comes out 0775 -- and fakts then
refused to read its own cache and silently re-ran the device-code flow.
"""

from __future__ import annotations

import os
import stat
from pathlib import Path
from typing import Iterator

import pytest
from arkitekt.app.fakts import _adopt_legacy_cache, _cache_path
from arkitekt.utils import create_arkitekt_folder
from fakts.models import Manifest


def make_manifest(identifier: str = "room-assistant") -> Manifest:
    return Manifest(identifier=identifier, version="0.0.1", scopes=["openid"])


@pytest.fixture
def loose_umask() -> Iterator[None]:
    """The layout that caused the bug, rather than pytest's private 0700."""
    previous = os.umask(0o002)
    try:
        yield
    finally:
        os.umask(previous)


@pytest.mark.skipif(os.name != "posix", reason="POSIX permission semantics")
def test_arkitekt_folder_is_private(tmp_path: Path, loose_umask: None) -> None:
    """Both levels, not just `cache/`: the folder also holds `servers/` and the
    credential JSONs its own generated .gitignore exists to hide."""
    create_arkitekt_folder(base_dir=str(tmp_path), with_cache=True)

    folder = tmp_path / ".arkitekt"
    assert stat.S_IMODE(folder.stat().st_mode) == 0o700
    assert stat.S_IMODE((folder / "cache").stat().st_mode) == 0o700


@pytest.mark.skipif(os.name != "posix", reason="POSIX permission semantics")
def test_arkitekt_folder_narrows_an_existing_loose_folder(
    tmp_path: Path, loose_umask: None
) -> None:
    """The usual case: the directory already exists at 0775 because an earlier
    version created it, and `exist_ok=True` applies no mode to it."""
    existing = tmp_path / ".arkitekt" / "cache"
    existing.mkdir(parents=True)
    os.chmod(existing, 0o775)
    os.chmod(tmp_path / ".arkitekt", 0o775)

    create_arkitekt_folder(base_dir=str(tmp_path), with_cache=True)

    assert stat.S_IMODE(existing.stat().st_mode) == 0o700


def test_cache_path_follows_the_user_not_the_cwd() -> None:
    """It used to be relative to the working directory, so the same app run
    from two places kept two sessions and re-authenticated in each."""
    path = _cache_path(make_manifest(), "https://go.arkitekt.live")

    assert os.path.isabs(path)
    assert ".arkitekt" not in path
    assert os.path.basename(path).startswith("room-assistant-0.0.1-")


def test_cache_path_separates_two_servers() -> None:
    """Without the url in the *filename* these collide, and because a
    different url invalidates the hash they would evict each other on every
    run -- a device-code prompt on every start."""
    manifest = make_manifest()

    lab = _cache_path(manifest, "https://go.arkitekt.live")
    local = _cache_path(manifest, "http://localhost:8000")

    assert lab != local
    assert os.path.dirname(lab) == os.path.dirname(local)


def _legacy_cache(tmp_path: Path, manifest: Manifest, payload: str) -> Path:
    legacy = tmp_path / ".arkitekt" / "cache"
    legacy.mkdir(parents=True)
    path = legacy / f"{manifest.identifier}-{manifest.version}_fakts_cache.json"
    path.write_text(payload)
    return path


def test_legacy_cache_is_adopted_rather_than_orphaned(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Relocating the cache must not cost one re-authentication per app."""
    manifest = make_manifest()
    monkeypatch.chdir(tmp_path)
    _legacy_cache(tmp_path, manifest, '{"hello": "world"}')
    new_path = tmp_path / "state" / "cache.json"
    new_path.parent.mkdir()

    _adopt_legacy_cache(manifest, str(new_path))

    assert new_path.read_text() == '{"hello": "world"}'
    if os.name == "posix":
        assert stat.S_IMODE(new_path.stat().st_mode) == 0o600


def test_adoption_leaves_the_legacy_file_in_place(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """So that rolling this change back keeps working."""
    manifest = make_manifest()
    monkeypatch.chdir(tmp_path)
    legacy = _legacy_cache(tmp_path, manifest, "{}")
    new_path = tmp_path / "state" / "cache.json"
    new_path.parent.mkdir()

    _adopt_legacy_cache(manifest, str(new_path))

    assert legacy.exists()


def test_adoption_never_overwrites_an_existing_session(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The legacy file is stale by definition once we have a new one; adopting
    over it would roll the session back to a revoked refresh token."""
    manifest = make_manifest()
    monkeypatch.chdir(tmp_path)
    _legacy_cache(tmp_path, manifest, '{"stale": true}')
    new_path = tmp_path / "state" / "cache.json"
    new_path.parent.mkdir()
    new_path.write_text('{"current": true}')

    _adopt_legacy_cache(manifest, str(new_path))

    assert new_path.read_text() == '{"current": true}'


def test_adoption_is_a_no_op_without_a_legacy_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    new_path = tmp_path / "state" / "cache.json"
    new_path.parent.mkdir()

    _adopt_legacy_cache(make_manifest(), str(new_path))

    assert not new_path.exists()


def test_no_empty_cache_folder_is_created_by_default(tmp_path: Path) -> None:
    """The session cache moved to a per-user directory, so creating
    `.arkitekt/cache/` would leave an empty folder nothing ever writes to."""
    create_arkitekt_folder(base_dir=str(tmp_path))

    assert not (tmp_path / ".arkitekt" / "cache").exists()
