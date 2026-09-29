"""How a run connects: the deployment side of a run, nothing about the app."""

from typing import Any

from fakts.mesh import MeshOptions, MeshProxy
from pydantic import BaseModel, ConfigDict


class ConnectionOptions(BaseModel):
    """How a run connects. Everything here is about the deployment, nothing about the app.

    What is passed wins; then the environment (``FAKTS_URL``, ``FAKTS_TOKEN``,
    ``FAKTS_REDEEM_TOKEN``, ``ARKITEKT_MESH_PROXY``, ``ARKITEKT_MESH``); then the
    defaults. :func:`connect` documents each.
    """

    url: str | None = None
    token: str | None = None
    redeem_token: str | None = None
    no_cache: bool = False
    headless: bool = False
    # Held as Any: pydantic cannot build a schema for the hook's callable type.
    device_code_hook: Any | None = None
    force: bool = False
    """Take over an existing registration of this app's agent. Applied to the
    run's agent; the app and its clients know nothing of it."""
    device_id: str | None = None
    mesh: MeshOptions | MeshProxy | bool | None = None
    """How to reach mesh-only services (``True`` runs a node, ``False`` is off);
    ``None`` defers to ``$ARKITEKT_MESH_PROXY`` and ``$ARKITEKT_MESH`` (see
    :func:`arkitekt.app.fakts.mesh_from_env`)."""

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")
