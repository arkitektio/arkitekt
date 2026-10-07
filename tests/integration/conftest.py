"""Fixtures for the tests that run an app against a real deployment.

The deployment is built by konstruktor (https://github.com/arkitektio/konstruktor),
through its ``konstruktor_hub`` fixture: a self-contained hub -- services and a
coordination server of their own -- that nobody has to accept, so the whole suite
runs unattended. Nothing here knows what such a deployment consists of; that is
konstruktor's.

What *is* decided here is what every other test in this repository takes for
granted and these must not: that fakts is offline.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Iterator

import pytest

if TYPE_CHECKING:
    from konstruktor import Hub


@pytest.fixture(autouse=True)
def _offline_fakts() -> None:
    """Leave fakts alone: these tests are the ones that talk to a server.

    Shadows the fixture of the same name in ``tests/conftest.py``, which swaps a
    ``TestingFakts`` in for every other test.
    """


@pytest.fixture(scope="session", autouse=True)
def _private_session_state(tmp_path_factory: pytest.TempPathFactory) -> Iterator[None]:
    """Keep the sessions these tests log in with out of the user's own.

    An app caches its session per identifier, version and server under the user's
    state directory. A hub gets a new port on every run, so each run would leave
    a file behind there for every app it connects.

    Also turns the mesh off: a self-contained hub has none, and the default is to
    look for one.
    """
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("XDG_STATE_HOME", str(tmp_path_factory.mktemp("state")))
        patch.setenv("ARKITEKT_MESH", "0")
        yield


@pytest.fixture(scope="session")
def hub(konstruktor_hub) -> "Hub":  # noqa: ANN001 -- konstruktor's factory fixture
    """One deployment for the whole session: rekuest and mikro.

    Made from the images the two client packages say host them, which is all
    either has to know about its server. One redeem token serves one app, so
    there is one for every app the tests connect. Each test takes its own with
    ``hub.redeem_token(<a name>)``.
    """
    from mikro import mikro_service
    from rekuest.arkitekt import rekuest_service

    return konstruktor_hub(
        service_images=[rekuest_service.image, mikro_service.image], redeem_tokens=8
    )
