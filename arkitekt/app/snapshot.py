"""What one run of an app serves: taken from the declaration, never changed by it.

An :class:`~arkitekt.App` is a declaration. A :class:`RunSnapshot` is what a
particular run of it offers, is, and can build -- taken once, at the moment the
run connects, because that is what it tells the server.

Three things travel together because a run needs all three and none of them may
drift from the others:

* the **manifest**, with this machine's node id resolved into it,
* the **registry**, frozen and validated, holding what the run serves -- the
  clients the run builds (or is handed) included.

Keeping them in one object is what lets a :class:`~arkitekt.runtime.Runtime` hold
a single reference instead of an app *and* a registry that looks like the app's
but is not (it is the frozen copy).
"""

from typing import Any

from arkitekt_spec.declare.app import AppRegistry
from arkitekt_spec.declare.client import ClientDeclaration
from arkitekt_spec.declare.provider import Provider
from fakts.models import Manifest
from pydantic import BaseModel, ConfigDict


class RunSnapshot(BaseModel):
    """What a run of an app serves: its manifest and its frozen registry.

    Built by :meth:`arkitekt.App.snapshot`. Taking it validates the declaration,
    so a port naming a structure the app cannot resolve fails here -- before
    anything connects -- rather than mid-assignment.

    Attributes:
        manifest: What the run tells the server it is, with the device id resolved.
        registry: What the run serves, the clients it uses included. Frozen:
            registering on it raises, because a run offers what was declared
            when it started.
    """

    manifest: Manifest
    registry: AppRegistry

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True, extra="forbid")

    @property
    def clients(self) -> dict[str, ClientDeclaration[Any]]:
        """The clients the run builds or is handed, by name."""
        return self.registry.clients

    @property
    def provider(self) -> "Provider[Any] | None":
        """What builds the run's agent, or ``None`` for a run that serves nothing."""
        return self.registry.provider


__all__ = ["RunSnapshot"]
