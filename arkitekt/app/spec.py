"""The App, said in the wire format every consumer reads (:mod:`arkitekt_spec`).

This is the one place an :class:`~arkitekt.app.app.App` is turned into its spec
models. :func:`app_declaration` is the whole app as one document; the rest are views
of it: the login manifest (``App.manifest``, built on :func:`app_manifest`), what the
plugin build records (:func:`app_manifest`), and what ``arkitekt inspect all``
emits inside the built image (:func:`app_inspection`). Both used to be assembled
separately against kabinet's GraphQL inputs, which is how the agent ``description``
reached a model that did not know it.
"""

from collections.abc import Sequence
from typing import TYPE_CHECKING, Protocol

from arkitekt_spec import (
    DEFAULT_ENTRYPOINT,
    UNKNOWN_AUTHOR,
    AppDeclaration,
    AppManifest,
    Inspection,
)

if TYPE_CHECKING:
    from arkitekt.app.snapshot import RunSnapshot


class DeclaredApp(Protocol):
    """Who an app is, as the spec shapes read it (an :class:`~arkitekt.app.app.App`)."""

    @property
    def identifier(self) -> str:
        """Globally unique identifier."""
        ...

    @property
    def version(self) -> str:
        """The app's version."""
        ...

    @property
    def author(self) -> str | None:
        """Who wrote it."""
        ...

    @property
    def description(self) -> str | None:
        """What it is, in a sentence."""
        ...

    @property
    def logo(self) -> str | None:
        """A public url of its logo."""
        ...

    @property
    def scopes(self) -> Sequence[str]:
        """The scopes it requests."""
        ...


def app_manifest(app: DeclaredApp, entrypoint: str = DEFAULT_ENTRYPOINT) -> AppManifest:
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


def app_declaration(
    app: DeclaredApp, run: "RunSnapshot", entrypoint: str = DEFAULT_ENTRYPOINT
) -> AppDeclaration:
    """Everything the app is, as one document: the source of every other shape.

    ``run`` is the snapshot a run would serve (see ``App.snapshot``), so the
    provider's structures and requirements are in it. The action language comes
    from ``to_implement_agent_input``, which builds it in :mod:`arkitekt_spec.actions`
    models and runs rekuest's own checks on it.
    """
    agent = run.registry.to_implement_agent_input(description=app.description)
    return AppDeclaration(
        manifest=app_manifest(app, entrypoint),
        requirements=list(run.manifest.requirements or ()),
        implementations=list(agent.implementations or ()),
        states=list(agent.states or ()),
        locks=list(agent.locks or ()),
        bloks=list(agent.bloks or ()),
    )


def app_inspection(app: DeclaredApp, run: "RunSnapshot") -> Inspection:
    """What a built image records about the app: its declaration, as an inspection."""
    return app_declaration(app, run).to_inspection()
