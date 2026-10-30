"""Read what an earlier run knew, after a restart or a power cut.

``@app.state(persist=...)`` keeps the state's last value on disk, and a startup hook of
the next run takes it as ``old: Stage | None``. Asking for a state without ``persist`` is
refused when the app is declared.

- ``persist=1.0`` writes at most once a second, off the event loop. A power cut loses
  about that much.
- ``persist="synchronous"`` writes every change and fsyncs it on the event loop. Nothing
  is lost, so keep it for states that change rarely.

``old`` is what the agent last knew, not what the hardware did: here the stage may have
moved after that last write, so the hook reads the real position and compares. It is
``None`` on a first run, after a version bump, or when the state's fields changed.
"""

from arkitekt import App, run

app = App("stage", "0.1.0")


@app.state(name="stage", persist=1.0)
class Stage:
    """Where the stage is, and whether it stopped where it was last known to be."""

    position_um: float = 0.0
    moved_while_down: bool = False


def read_encoder() -> float:
    """Reads the stage's real position."""
    return 12.5


@app.startup
def start(old: Stage | None) -> Stage:
    position_um = read_encoder()
    moved = old is not None and abs(old.position_um - position_um) > 0.1
    return Stage(position_um=position_um, moved_while_down=moved)


if __name__ == "__main__":
    run(app)
