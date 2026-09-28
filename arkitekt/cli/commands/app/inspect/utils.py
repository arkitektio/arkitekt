"""What the inspect commands share: reading what a run of an App would serve, without running it."""

from arkitekt_spec.declare.app import AppRegistry

from arkitekt.app.app import App
from arkitekt.app.snapshot import RunSnapshot
from arkitekt.cli.errors import cli_error
from arkitekt.runtime import _provider_for

NOTHING_TO_PROVIDE = "This app offers nothing: no action, state, hook or blok."


def run_snapshot_or_exit(app: App) -> RunSnapshot:
    """What a run of the App would serve; an invalid declaration exits cleanly.

    The snapshot is taken the way ``run(app)`` takes it: with the provider a run
    would use (the app's own, or rekuest's when it offers something), so the
    services, structures and requirements that provider brings are in it. It is
    checked the way a run checks it, with no clients bound -- inspecting never
    connects. It fails when a port names a structure the App cannot resolve
    (usually an undeclared service), which is worth a clear error rather than a
    traceback.

    Without rekuest installed there is no provider to take it with: the snapshot is
    then the app as declared, without the requirements rekuest's provider adds.
    """
    try:
        return app.snapshot(provider=_provider_for(app, required=False))
    except Exception as e:
        cli_error(f"The app '{app.identifier}' is not valid: {e}")


def snapshot_or_exit(app: App) -> AppRegistry:
    """The registry a run of the App would serve; see :func:`run_snapshot_or_exit`."""
    return run_snapshot_or_exit(app).registry
