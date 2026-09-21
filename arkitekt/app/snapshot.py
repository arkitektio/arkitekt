"""What one run of an app serves: taken from the declaration, never changed by it.

An :class:`~arkitekt.App` is a declaration. A :class:`RunSnapshot` is what a
particular run of it offers, is, and can build -- taken once, at the moment the
run connects, because that is what it tells the server.

Three things travel together because a run needs all three and none of them may
drift from the others:

* the **manifest**, with this machine's node id resolved into it,
* the **registry**, frozen and validated, holding what the run serves -- the
  services the run may build clients for included, since they are registered
  on it.

Keeping them in one object is what lets a :class:`~arkitekt.runtime.Runtime` hold
a single reference instead of an app *and* a registry that looks like the app's
but is not (it is the frozen copy).
"""

from typing import Dict

from typing import Any, Optional

from fakts.models import Manifest
from pydantic import BaseModel, ConfigDict
from rekuest.app import AppRegistry
from rekuest.provider import Provider
from rekuest.service import Service


class RunSnapshot(BaseModel):
    """What a run of an app serves: its manifest and its frozen registry.

    Built by :meth:`arkitekt.App.snapshot`. Taking it validates the declaration,
    so a port naming a structure the app cannot resolve fails here -- before
    anything connects -- rather than mid-assignment.

    Attributes:
        manifest: What the run tells the server it is, with the device id resolved.
        registry: What the run serves, the services it uses included. Frozen:
            registering on it raises, because a run offers what was declared
            when it started.
    """

    manifest: Manifest
    registry: AppRegistry

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True, extra="forbid")

    @property
    def services(self) -> Dict[str, Service]:
        """The services the run may build clients for, by name: the registry's."""
        return self.registry.services

    @property
    def providers(self) -> Dict[str, "Provider[Any]"]:
        """The providers the run may build its agent from, by name: the registry's."""
        return self.registry.providers

    @property
    def provider(self) -> Optional["Provider[Any]"]:
        """The one provider the app declared, or ``None`` for an app offering nothing."""
        return self.registry.provider_declaration

    @property
    def app_context_class(self) -> Optional[type]:
        """The class the run's ``context=`` must be an instance of, or ``None``."""
        return self.registry.app_context_class

    @property
    def needs_fakts(self) -> bool:
        """Whether a run of this snapshot resolves anything through fakts."""
        return any(s.needs_fakts for s in self.services.values()) or (
            self.provider is not None and self.provider.needs_fakts
        )


__all__ = ["RunSnapshot"]
