"""Unit tests for ``plugin.build.inspect_all``'s stall bound.

``inspect_all`` runs ``arkitekt-next inspect all`` inside the freshly built
container. If that container never emits the ``--END_AGENT--`` sentinel (or
hangs on import), the read must not block the build forever -- ``communicate``
is bounded by ``INSPECTION_TIMEOUT_SECONDS`` and the container is killed. This
mocks the subprocess boundary so it needs no docker.
"""

import subprocess
from unittest.mock import patch

import pytest

from arkitekt_next.cli.commands.plugin.build import (
    INSPECTION_TIMEOUT_SECONDS,
    InspectionError,
    inspect_all,
)

BUILD = "arkitekt_next.cli.commands.plugin.build"


class _HangingProc:
    """A container process whose bounded ``communicate`` always times out."""

    returncode = None

    def __init__(self):
        self.killed = False

    def communicate(self, timeout=None):
        if timeout is not None:
            raise subprocess.TimeoutExpired(cmd="docker run", timeout=timeout)
        return (b"", b"")  # the post-kill drain

    def kill(self):
        self.killed = True
        self.returncode = -9


def test_inspect_all_times_out_instead_of_hanging():
    proc = _HangingProc()
    with patch(f"{BUILD}.subprocess.Popen", return_value=proc):
        with pytest.raises(InspectionError) as exc:
            inspect_all("build-123", "http://fakts.example")

    # The wedged container was killed and the timeout reported.
    assert proc.killed
    assert "timed out" in str(exc.value)
    assert str(INSPECTION_TIMEOUT_SECONDS) in str(exc.value)


class _OkProc:
    """A container that returns a well-formed inspection payload promptly."""

    returncode = 0

    def communicate(self, timeout=None):
        payload = b"noise\n--START_AGENT--{\"implementations\": []}--END_AGENT--\n"
        return (payload, b"")

    def kill(self):  # pragma: no cover - not reached on the happy path
        pass


def test_inspect_all_parses_payload_within_bound():
    with patch(f"{BUILD}.subprocess.Popen", return_value=_OkProc()):
        result = inspect_all("build-123", "http://fakts.example")

    assert result == {"implementations": []}
