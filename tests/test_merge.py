"""Declare an app in parts: ``merge(a, b)`` is one registry, which runs as an app."""

from typing import AsyncIterator

from arkitekt import App, AppRegistry, merge

from .fakes import RekuestProvider


def test_parts_merge_into_a_registry_that_runs_as_one_app() -> None:
    # Both use one provider, as two parts using one service do: that counts once.
    provider = RekuestProvider()
    stage = App("stage", "1", providers=[provider])
    camera = App("camera", "1", providers=[provider])
    extras = AppRegistry()

    @stage.action
    def move(x: int) -> int:
        """Moves the stage."""
        return x

    @camera.state(name="camera", persist=1.0)
    class Camera:
        exposure: int = 1

    @camera.lifecycle
    async def connect() -> AsyncIterator[Camera]:
        yield Camera()

    @extras.register
    def snap(x: int) -> int:
        """Takes a picture."""
        return x

    merged = merge(stage, camera, extras)
    assert isinstance(merged, AppRegistry)

    snapshot = App("microscope", "1", registry=merged).snapshot()

    assert set(snapshot.registry.implementations) >= {"move", "snap"}
    assert snapshot.registry.structure_registry.state_for(Camera).persist == 1.0
    assert "connect" in snapshot.registry.hooks_registry.startup_hooks
    assert "snap" not in stage.registry.implementations, "the parts are not changed"
    assert "snap" in App("into", "1").merge(extras).registry.implementations
