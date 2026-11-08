"""Say, once a command is done, when a newer arkitekt is out.

`uvx arkitekt` keeps running the version it cached, and a project keeps the one
its lockfile pins: neither says that a newer one exists. So, at most once a day,
a command asks PyPI in the background, keeps the answer, and when what it found
is newer than what runs, says so on stderr after the command's own output.

It never holds a command up: the question runs in a daemon thread, and an answer
that is not in when the command ends is left for the next one. It is not asked at
all where nobody would read the notice (stderr is not a terminal, or CI), or when
``ARKITEKT_NO_UPDATE_CHECK`` is set.
"""

import json
import os
import sys
import threading
import time
import urllib.request
from typing import Any

from rich.console import Console

#: Set to anything to never ask.
DISABLE_ENV = "ARKITEKT_NO_UPDATE_CHECK"

#: How long an answer is kept before PyPI is asked again.
CHECK_EVERY_SECONDS = 24 * 60 * 60

#: How long the background question may take before it is given up.
TIMEOUT_SECONDS = 3.0

#: How long a command that is done waits for an answer still on its way: only on
#: the day's one question, and short, so a quick command still learns the answer.
WAIT_AT_CLOSE_SECONDS = 1.0

PYPI_URL = "https://pypi.org/pypi/arkitekt/json"


def _cache_file() -> str:
    from platformdirs import user_cache_dir

    from arkitekt.constants import APP_AUTHOR, APP_NAME

    return os.path.join(user_cache_dir(APP_NAME, APP_AUTHOR), "latest-release.json")


def _read_cache(path: str) -> dict[str, Any] | None:
    try:
        with open(path, encoding="utf-8") as file:
            cached = json.load(file)
    except (OSError, ValueError):
        return None
    return cached if isinstance(cached, dict) else None


def _write_cache(path: str, latest: str, now: float) -> None:
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        partial = f"{path}.partial"
        with open(partial, "w", encoding="utf-8") as file:
            json.dump({"latest": latest, "checked_at": now}, file)
        os.replace(partial, path)
    except OSError:
        pass


def fetch_latest(timeout: float = TIMEOUT_SECONDS) -> str | None:
    """The newest arkitekt release on PyPI, or None when PyPI cannot be asked."""
    try:
        with urllib.request.urlopen(PYPI_URL, timeout=timeout) as response:  # noqa: S310
            return str(json.load(response)["info"]["version"])
    except Exception:
        return None


def is_newer(latest: str, current: str) -> bool:
    """Whether ``latest`` is a newer release than ``current``, by PEP 440.

    A development or local build (a source checkout, ``13.4.1.dev0+g…``) is never
    told: it is not a release that could be upgraded.
    """
    try:
        from packaging.version import InvalidVersion, Version
    except ImportError:  # not ours to require: semver is, and it reads plain releases
        import semver

        try:
            return semver.Version.parse(latest) > semver.Version.parse(current)
        except ValueError:
            return False
    try:
        running, newest = Version(current), Version(latest)
    except InvalidVersion:
        return False
    if running.is_devrelease or running.local:
        return False
    return newest > running


def wanted(environ: dict[str, str] | None = None, stderr: Any = None) -> bool:  # noqa: ANN401
    """Whether to ask at all: someone reads stderr, it is not CI, and it is not turned off."""
    environ = dict(os.environ) if environ is None else environ
    if environ.get(DISABLE_ENV) or environ.get("CI"):
        return False
    stream = sys.stderr if stderr is None else stderr
    try:
        return bool(stream.isatty())
    except (AttributeError, ValueError):
        return False


def upgrade_hint(work_dir: str | None) -> str:
    """How the arkitekt that runs is moved to the newest one."""
    prefix = sys.prefix.replace(os.sep, "/")
    if "/uv/archive-v" in prefix:
        # An environment uvx made for `uvx arkitekt`: it stays on the version it cached.
        return "uvx arkitekt@latest"
    from arkitekt.cli.ui import command_hint

    return command_hint("self upgrade", work_dir)


class UpdateCheck:
    """One command's look at whether a newer arkitekt is out."""

    def __init__(
        self, current: str, cache_file: str | None = None, now: float | None = None, work_dir: str | None = None
    ) -> None:
        self.current = current
        self.work_dir = work_dir
        self.cache_file = cache_file or _cache_file()
        self.now = time.time() if now is None else now
        self._fetched: list[str | None] = []
        self._thread: threading.Thread | None = None
        cached = _read_cache(self.cache_file)
        self.latest: str | None = cached.get("latest") if cached else None
        fresh = cached is not None and self.now - float(cached.get("checked_at", 0)) < CHECK_EVERY_SECONDS
        if not fresh:
            self._thread = threading.Thread(target=self._fetch, name="arkitekt-update-check", daemon=True)
            self._thread.start()

    def _fetch(self) -> None:
        latest = fetch_latest()
        if latest:
            # Kept as soon as it is in: a command that ends first still leaves it for the next.
            _write_cache(self.cache_file, latest, self.now)
        self._fetched.append(latest)

    def finish(self, console: Console, wait: float = WAIT_AT_CLOSE_SECONDS) -> None:
        """Say so when the newest release is newer than what runs."""
        if self._thread is not None:
            self._thread.join(timeout=wait)
            if self._fetched and self._fetched[0]:
                self.latest = self._fetched[0]
        if self.latest and is_newer(self.latest, self.current):
            from arkitekt.app.terminal import notice

            notice(
                console,
                f"arkitekt {self.latest} is out (this is {self.current})",
                f"`{upgrade_hint(self.work_dir)}`",
            )


def start(ctx: Any) -> None:  # noqa: ANN401
    """Begin the look for a command, and have it said when the command closes."""
    from arkitekt.cli.ui import arkitekt_version

    current = arkitekt_version()
    if current is None or not wanted():
        return
    from arkitekt.cli.vars import get_work_dir

    check = UpdateCheck(current, work_dir=get_work_dir(ctx))
    ctx.call_on_close(lambda: check.finish(Console(stderr=True)))


__all__ = ["UpdateCheck", "fetch_latest", "is_newer", "start", "upgrade_hint", "wanted"]
