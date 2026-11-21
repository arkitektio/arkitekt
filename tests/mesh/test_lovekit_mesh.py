"""Two apps, each on a mesh node of its own, exchange a lovekit data stream over a hub's mesh.

One app publishes a spectrum, the other watches it. Both log in at the gateway with a
mandate key and are told to take the mesh and nothing else (``MeshOptions(force=True)``), so
each resolves lovekit and its media server as mesh aliases:

- GraphQL (declaring, asking for a connection) goes through each app's mesh proxy;
- the media server's signalling goes through a forward of the app's node;
- the media goes through the node's relay, which reaches peers of the mesh only. The hub's
  media server shares the network of the hub's mesh sidecar, so its tailnet address is one
  it offers.

Needs Docker, ``konstruktor`` and ``lovekit``. The mesh workflow runs it
(``.github/workflows/mesh.yaml``); locally: ``uv run pytest tests/mesh -m mesh -rs``.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

pytestmark = [pytest.mark.mesh, pytest.mark.needs_docker]

pytest.importorskip("konstruktor", reason="builds the hub the apps log in to")
pytest.importorskip("lovekit", reason="the service the apps exchange a stream through")
np = pytest.importorskip("numpy")

from fakts.mesh import MeshOptions  # noqa: E402
from lovekit import Axis, AxisType, DataStream, lovekit_service  # noqa: E402
from lovekit.api.schema import StreamKind  # noqa: E402
from lovekit.lovekit import Lovekit  # noqa: E402

from arkitekt import App, connect  # noqa: E402

if TYPE_CHECKING:
    from konstruktor import Hub

SPECTRUM = DataStream("spectrum", dtype="float16", shape=(512,), axes=[Axis("wavelength", AxisType.SPECTRUM)])


@pytest.fixture
def own_state(hub: Hub, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Sessions and mesh nodes of these apps, out of the user's own; the hub's mesh, trusted."""
    assert hub.mesh is not None, "the hub was made with a mesh, and says of none"
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("ARKITEKT_MESH_CA_FILE", str(hub.mesh.ca_file))


def on_the_mesh(hub: Hub, name: str):  # noqa: ANN201
    """An app of its own identifier (so a mesh node of its own), logged in and on the mesh alone."""
    app = App(f"live.arkitekt.tests.{name}", "0.1.0", services=[lovekit_service])
    return connect(
        app,
        url=hub.fakts_url,
        mandate_key=hub.mandate_key(name),
        device_id=name,
        mesh=MeshOptions(force=True),
    )


@pytest.mark.asyncio
async def test_two_apps_exchange_a_data_stream_over_the_mesh(hub: Hub, own_state: None) -> None:
    values = np.linspace(0, 1, 512, dtype=np.float16)

    async with on_the_mesh(hub, "spectrometer") as publishing, on_the_mesh(hub, "viewer") as viewing:
        spectrometer, viewer = publishing.require(Lovekit), viewing.require(Lovekit)
        # Each on a node of its own: the media server is an alias its node carries.
        media, watched = spectrometer.livekit, viewer.livekit
        assert media is not None and watched is not None
        assert media.is_mesh() and watched.is_mesh()
        assert media.proxy != watched.proxy

        async with spectrometer.publish([SPECTRUM]) as live:
            await live.wait_connected(timeout=120)
            await live.data("spectrum").send(values)

            # The viewer knows the stream only from lovekit, as any other app would.
            [stream] = [s for s in await viewer.alist_streams() if s.kind == StreamKind.DATA]
            assert stream.id == live.streams[0].id

            async with viewer.watch(stream) as frames:
                # Nothing new is sent: a late viewer gets the last value, sent again.
                frame = await asyncio.wait_for(anext(frames), 120)
            assert (frame.values == values).all()
