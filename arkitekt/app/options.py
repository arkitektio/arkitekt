"""How a run connects: the deployment side of a run, nothing about the app."""

from typing import Any

from fakts.mesh import MeshOptions, MeshProxy
from pydantic import BaseModel, ConfigDict


class ConnectionOptions(BaseModel):
    """How a run connects. Everything here is about the deployment, nothing about the app.

    What is passed wins; then the environment (``FAKTS_URL``, ``FAKTS_TOKEN``,
    ``FAKTS_REDEEM_TOKEN``, ``ARKITEKT_REAUTH``, ``ARKITEKT_MESH_PROXY``,
    ``ARKITEKT_MESH``); then the
    defaults. :func:`connect` documents each.
    """

    url: str | None = None
    token: str | None = None
    redeem_token: str | None = None
    skip_cache: bool = False
    """Neither read nor write the fakts cache: the session lives in memory only."""
    reauth: bool = False
    """Log in again even when a session is cached, then cache the new one.
    ``False`` defers to ``$ARKITEKT_REAUTH``."""
    headless: bool = False
    # Held as Any: pydantic cannot build a schema for the hook's callable type.
    device_code_hook: Any | None = None
    force: bool = False
    """Take over an existing registration of this app's agent. Applied to the
    run's agent; the app and its clients know nothing of it."""
    # Held as Any, like the hook above.
    connection_listener: Any | None = None
    """Told when the server acknowledges the run's agent and when the link to it
    drops (``arkitekt_runtime.agents.connection``). Applied to the run's agent."""
    device_id: str | None = None
    mesh: MeshOptions | MeshProxy | bool | None = None
    """How to reach mesh-only services (``True`` runs a node, ``False`` is off);
    ``None`` defers to ``$ARKITEKT_MESH_PROXY`` and ``$ARKITEKT_MESH`` (see
    :func:`arkitekt.app.fakts.mesh_from_env`)."""

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")
