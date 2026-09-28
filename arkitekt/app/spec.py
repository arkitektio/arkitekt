"""The App, said in the wire format every consumer reads (:mod:`arkitekt_spec`).

This is the one place an :class:`~arkitekt.app.app.App` is turned into its spec
models: the plugin build records :func:`app_manifest`, and ``arkitekt inspect all``
(run inside the built image) emits :func:`app_inspection`. Both used to be assembled
separately against kabinet's GraphQL inputs, which is how the agent ``description``
reached a model that did not know it.
"""

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

from arkitekt_spec import (
    DEFAULT_ENTRYPOINT,
    UNKNOWN_AUTHOR,
    AppManifest,
    Inspection,
    Requirement,
)

if TYPE_CHECKING:
    from pydantic import BaseModel

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
    validated by rekuest (``to_implement_agent_input``) and carried as JSON.
    """
    agent = run.registry.to_implement_agent_input(description=app.description)
    return Inspection(
        description=app.description,
        requirements=[
            Requirement.model_validate(requirement.model_dump())
            for requirement in run.manifest.requirements or []
        ],
        implementations=entries(agent.implementations),
        states=entries(agent.states),
        locks=entries(agent.locks),
        bloks=entries(agent.bloks),
    )


def entries(items: "Sequence[BaseModel] | None") -> list[dict[str, Any]]:
    """rekuest models as the JSON the spec carries: camelCase, unset fields left out."""
    return [item.model_dump(mode="json", by_alias=True, exclude_none=True) for item in items or ()]
