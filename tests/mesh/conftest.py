"""What the mesh tests share: one hub with a mesh of its own, and real logins.

One hub for all of them: a hub with Lovekit brings a media server whose ports are fixed, so
two such hubs cannot run on one machine at a time.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from konstruktor import Hub


@pytest.fixture(autouse=True)
def _offline_fakts() -> None:
    """Leave fakts alone: these tests log in to a server.

    Shadows the fixture of the same name in ``tests/conftest.py``, which swaps a
    ``TestingFakts`` in for every other test.
    """


@pytest.fixture(scope="session")
def hub() -> Iterator[Hub]:
    """mikro and lovekit (with its media server), on a hub with a mesh of its own."""
    konstruktor = pytest.importorskip(
        "konstruktor", reason="builds the hub the apps log in to"
    )
    mikro = pytest.importorskip("mikro", reason="a service the apps call")
    lovekit = pytest.importorskip("lovekit", reason="a service the apps call")

    with konstruktor.testing_hub(
        name="meshhub",
        service_images=[mikro.mikro_service.image, lovekit.lovekit_service.image],
        mandate_keys=3,
        mesh=True,
    ) as hub:
        hub.up()
        hub.wait_ready()
        yield hub
