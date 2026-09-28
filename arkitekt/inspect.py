"""Open objects in the orkestrator desktop app."""

import typing
import webbrowser

from rath.scalars import ID

from arkitekt.runtime import Runtime

if typing.TYPE_CHECKING:
    from arkitekt.app.app import App


def open_orkestrator_link(link: str) -> None:
    """Open an ``orkestrator://`` link with the system's handler.

    Args:
        link: The link to open.
    """
    webbrowser.open(link)


class IDBearer(typing.Protocol):
    """Anything with an ``id``: what the orkestrator can open."""

    id: ID


def inspect(x: IDBearer, app: "App[typing.Any] | Runtime[typing.Any]") -> None:
    """Open ``x`` in the orkestrator.

    Args:
        x: The object to open; its class must be a structure ``app`` declares.
        app: An app, or a run of one, whose structure registry names ``x``'s type.

    Raises:
        StructureRegistryError: If ``app`` declares no structure for ``type(x)``.
        LookupError: If ``app`` is a runtime that was never entered.
    """
    if isinstance(app, Runtime):
        # What a runtime serves is its snapshot, taken when it was entered.
        snapshot = app.snapshot
        if snapshot is None:
            raise LookupError(
                "This runtime was never entered, so it has no registry yet."
            )
        registry = snapshot.registry
    else:
        registry = app.registry
    identifier = registry.structure_registry.get_identifier_for_cls(type(x))
    open_orkestrator_link(f"orkestrator://{identifier}/{x.id}")
