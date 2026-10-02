"""The login sessions cached on this machine: where they live and what they say.

A session is what a login leaves behind, one file per app, version and server
(see :func:`session_path`). This module only reads and removes those files; a
run writes them through fakts. It never returns a token.
"""

import os
import time
from dataclasses import dataclass
from hashlib import sha256
from typing import List, Optional

from fakts.cache.file import CacheFile
from fakts.session import REFRESH_CHAIN_MAX_AGE, REFRESH_TOKEN_MAX_AGE
from platformdirs import user_state_dir

from arkitekt.constants import APP_AUTHOR, APP_NAME

#: What every session file ends in. Other clients keep their own files beside
#: them (``.rs.json``, ``.lock``), which are not ours to list or remove.
SUFFIX = "_fakts_cache.json"

#: A manifest hash is a sha256 hexdigest; the cache's binding is that, then the url.
_MANIFEST_HASH_LENGTH = 64


def cache_dir() -> str:
    """The private per-user directory the sessions live in."""
    return os.path.join(user_state_dir(APP_NAME, APP_AUTHOR), "cache")


def session_path(identifier: str, version: str, url: str) -> str:
    """Where the session of this app, at this version, on this server lives.

    It follows the user, beside the device id that already uses platformdirs,
    never the working directory: the same app run from two directories is one
    app with one session.

    The url is in the *filename*, not only in the cache's `hash=` binding.
    Without it, one app pointed at two servers (a lab and a local stack)
    would collide on one file, and since a different url invalidates the
    hash, each run would evict the other's session -- turning a shared path
    into a device-code prompt on every single start.
    """
    url_key = sha256(url.encode()).hexdigest()[:6]
    return os.path.join(cache_dir(), f"{identifier}-{version}-{url_key}{SUFFIX}")


@dataclass(frozen=True)
class Session:
    """What a cached session says about itself. Nothing here is a credential."""

    path: str
    name: str
    """The app and its version, as the file is named: ``{identifier}-{version}``.
    The two are not stored apart, and either may hold a hyphen."""
    url: Optional[str]
    """The server it was logged in at, or None for a file that does not say."""
    deployment: str
    logged_in_at: Optional[float]
    """When the login happened (unix ts): the start of the refresh chain, which
    survives every token rotation."""
    refreshed_at: Optional[float]
    manifest_hash: str = ""
    """The hash of the manifest it was approved for. A run whose manifest hashes
    differently does not use this session: it logs in again."""

    def is_for(self, manifest_hash: str) -> bool:
        """Whether a run sending the manifest of that hash would use this session."""
        return self.manifest_hash == manifest_hash

    def state(self, now: Optional[float] = None) -> str:
        """Whether the session can still be used, as far as this machine can tell.

        ``active``, ``idle`` (unused for longer than a refresh token lives) or
        ``expired`` (older than a login may get). The server has the last word.
        """
        now = time.time() if now is None else now
        if self.logged_in_at and now - self.logged_in_at > REFRESH_CHAIN_MAX_AGE:
            return "expired"
        if self.refreshed_at and now - self.refreshed_at > REFRESH_TOKEN_MAX_AGE:
            return "idle"
        return "active"


def read_session(path: str) -> Optional[Session]:
    """Read the session at ``path``, or None if there is none that can be read.

    Read as plain data: loading it through the cache would narrow its
    permissions and warn about them, which looking must not do.
    """
    try:
        with open(path, encoding="utf-8") as file:
            cached = CacheFile.model_validate_json(file.read())
    except (OSError, ValueError):
        return None

    stem = os.path.basename(path)[: -len(SUFFIX)]
    name, _, _ = stem.rpartition("-")
    url = cached.hash[_MANIFEST_HASH_LENGTH:] or None
    return Session(
        path=path,
        name=name or stem,
        url=url,
        deployment=cached.fakts.self.deployment_name,
        logged_in_at=cached.fakts.auth.chain_started_at,
        refreshed_at=cached.fakts.auth.refresh_issued_at,
        manifest_hash=cached.hash[:_MANIFEST_HASH_LENGTH],
    )


def list_sessions() -> List[Session]:
    """Every session cached on this machine, by name."""
    try:
        names = os.listdir(cache_dir())
    except OSError:
        return []
    sessions = [
        read_session(os.path.join(cache_dir(), name))
        for name in sorted(names)
        if name.endswith(SUFFIX)
    ]
    return [session for session in sessions if session is not None]


def forget(path: str) -> bool:
    """Remove the session at ``path``. Returns whether there was one.

    This forgets it on this machine only: nothing is revoked on the server, and
    a process still running on the session writes it back when its token rotates.
    """
    try:
        os.remove(path)
    except FileNotFoundError:
        return False
    return True


__all__ = [
    "SUFFIX",
    "Session",
    "cache_dir",
    "forget",
    "list_sessions",
    "read_session",
    "session_path",
]
