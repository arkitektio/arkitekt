"""The App, said in the wire format every consumer reads (:mod:`arkitekt_spec`).

This is the one place an :class:`~arkitekt.app.app.App` is turned into its spec
models: the plugin build records :func:`app_manifest`, and ``arkitekt inspect all``
(run inside the built image) emits :func:`app_inspection`. Both used to be assembled
separately against kabinet's GraphQL inputs, which is how the agent ``description``
reached a model that did not know it.
"""

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, TypeVar

from arkitekt_spec import (
    DEFAULT_ENTRYPOINT,
    UNKNOWN_AUTHOR,
    AppManifest,
    Inspection,
    Requirement,
)
from arkitekt_spec.actions import (
    BlokImplementationInput,
    ImplementationInput,
    LockImplementationInput,
    StateImplementationInput,
)
from pydantic import BaseModel

if TYPE_CHECKING:
    from arkitekt.app.app import App
    from arkitekt.app.snapshot import RunSnapshot


def app_manifest(app: "App[Any]", entrypoint: str = DEFAULT_ENTRYPOINT) -> AppManifest:
    """Who the app is.

    Args:
        app: The declaration.
        entrypoint: The target (``module[:attr]``) that finds the app, recorded so
            the image is run (and inspected) on the app it was built for.
    """
    return AppManifest(
        identifier=app.identifier,
        version=app.version,
        author=app.author or UNKNOWN_AUTHOR,
        description=app.description,
        logo=app.logo,
        scopes=list(app.scopes),
        entrypoint=entrypoint,
    )


def app_inspection(app: "App[Any]", run: "RunSnapshot") -> Inspection:
    """What a run of the app declares, and the services it requires.

    ``run`` is the snapshot a run would serve (see ``App.snapshot``), so the
    provider's structures and requirements are in it. The action language is
    validated twice: by rekuest (``to_implement_agent_input``) as it is built, and by
    the spec's :mod:`arkitekt_spec.actions` as it is converted -- so a field rekuest
    emits that the spec does not know fails here, at build time, not at the server.
    """
    agent = run.registry.to_implement_agent_input(description=app.description)
    return Inspection(
        description=app.description,
        requirements=[
            Requirement.model_validate(requirement.model_dump())
            for requirement in run.manifest.requirements or []
        ],
        implementations=convert(agent.implementations, ImplementationInput),
        states=convert(agent.states, StateImplementationInput),
        locks=convert(agent.locks, LockImplementationInput),
        bloks=convert(agent.bloks, BlokImplementationInput),
    )


SpecModel = TypeVar("SpecModel", bound=BaseModel)


def convert(items: "Sequence[BaseModel] | None", into: type[SpecModel]) -> list[SpecModel]:
    """rekuest's protocol models, re-read as the spec's (unset fields left to their defaults)."""
    return [
        into.model_validate(item.model_dump(mode="json", by_alias=True, exclude_none=True))
        for item in items or ()
    ]
