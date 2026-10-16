"""How a run connects: the deployment side of a run, nothing about the app."""

from typing import Any

from fakts.mesh import MeshOptions, MeshProxy
from pydantic import BaseModel, ConfigDict

from arkitekt.app.sources import DISCOVER, Source


class ConnectionOptions(BaseModel):
    """How a run connects. Everything here is about the deployment, nothing about the app.

    Each option a deployment may set from outside takes a value, ``None`` (none: nothing
    is used or looked up), or a :data:`~arkitekt.app.sources.Source` naming where to look
    (``"discover"``, the default: the command line, then the environment, then the
    built-in default). :func:`connect` documents each option's flag and variable.
    """

    url: str | Source | None = DISCOVER
    """The fakts server: ``--url``, ``$FAKTS_URL``, then the public deployment. A run
    cannot connect to no server, so ``None`` is read as ``"discover"``."""
    token: str | Source | None = DISCOVER
    """A previously issued credential: ``--token``, ``$FAKTS_TOKEN``; none by default."""
    mandate_key: str | Source | None = DISCOVER
    """A mandate key to log the app in with: ``--mandate-key``, ``$FAKTS_MANDATE_KEY``."""
    skip_cache: bool = False
    """Neither read nor write the fakts cache: the session lives in memory only."""
    reauth: bool | Source = DISCOVER
    """Log in again even when a session is cached, then cache the new one:
    ``--reauth``, ``$ARKITEKT_REAUTH``, else off."""
    headless: bool = False
    # Held as Any: pydantic cannot build a schema for the hook's callable type.
    device_code_hook: Any | None = None
    force: bool = False
    """Take over an existing registration of this app's agent. Applied to the
    run's agent; the app and its clients know nothing of it."""
    # Held as Any, like the hook above.
    connection_listener: Any | None = None
    """Told when the server acknowledges the run's agent and when the link to it
    drops (``arkitekt_spec.declare.agents.connection``). Applied to the run's agent."""
    # Held as Any, like the hook above.
    task_listener: Any | None = None
    """Told what happens to each task the run's agent takes: assigned (with its
    arguments), progress, yielded, done, failed, cancelled. Applied to the run's agent."""
    allow_insecure_transport: bool | Source = DISCOVER
    """Talk plain http to a server that is not on this machine: ``--allow-insecure-transport``,
    ``$FAKTS_ALLOW_INSECURE_TRANSPORT``, else off. Off, such a server is refused: its login
    would cross the network unencrypted."""
    device_id: str | Source | None = DISCOVER
    """This device's identity: ``--device-id``, ``$ARKITEKT_DEVICE_ID``, then the machine's id."""
    supervisor: str | Source | None = DISCOVER
    """The app that controls this process's lifecycle (e.g. ``plugin_engine``), stated on
    every Register: ``--supervisor``, ``$ARKITEKT_SUPERVISOR``; none by default."""
    mesh: MeshOptions | MeshProxy | bool | Source | None = DISCOVER
    """How to reach mesh-only services (``True`` runs a node, ``False`` or ``None`` is off):
    ``--mesh``, ``$ARKITEKT_MESH_PROXY`` / ``$ARKITEKT_MESH``, then auto (see
    :func:`arkitekt.app.fakts.mesh_from_env`)."""

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")
