"""A hand-registered structure whose expander asks for clients by annotation.

The service-owned path (``StructureDescription`` + ``declare``) is unchanged and
covered in rekuest. What is new here is the other path: a type a shared library
defines, fetched back through a client the run supplies.
"""

from typing import Any

import pytest
from arkitekt_spec.declare.service import Service
from arkitekt_spec.declare.structures.errors import StructureDefinitionError

from arkitekt import App, connect

from .fakes import PictureClient, PictureService, RekuestProvider


class Thing:
    """A type a shared library defines, fetched through someone else's client."""

    def __init__(self, id: str, owner: str) -> None:
        self.id = id
        self.owner = owner


async def expand_thing(id: str, pictures: PictureClient) -> Thing:
    """Fetch a Thing by id, through the run's pictures client."""
    return Thing(id, pictures.name)


def picture_app(*services: Service) -> App:
    """An app using the pictures service (and a fake rekuest), and any others given."""
    return App("structures", services=[PictureService(), *services], providers=[RekuestProvider()])


def bare_app() -> App:
    """An app using no service at all."""
    return App("structures")


# ------------------------------------------------------------------ #
# What it buys                                                       #
# ------------------------------------------------------------------ #


@pytest.mark.asyncio
async def test_an_expander_is_handed_the_runs_client() -> None:
    app = picture_app()
    app.register_structure(Thing, "@lib/thing", expand=expand_thing)

    async with connect(app) as rt:
        structure = rt.snapshot.registry.structure_registry.get_fullfilled_structure(
            "@lib/thing"
        )
        thing = await structure.expand("1")

    assert (thing.id, thing.owner) == ("1", rt.get(PictureClient).name)


@pytest.mark.asyncio
async def test_each_run_expands_through_its_own_client() -> None:
    """The per-run isolation `bind` exists to protect, for injected expanders too."""
    app = picture_app()
    app.register_structure(Thing, "@lib/thing", expand=expand_thing)

    def structure_of(rt: Any) -> Any:  # noqa: ANN401
        return rt.snapshot.registry.structure_registry.get_fullfilled_structure(
            "@lib/thing"
        )

    async with connect(app) as a:
        async with connect(app) as b:
            from_a = await structure_of(a).expand("1")
            from_b = await structure_of(b).expand("2")

    assert (from_a.owner, from_b.owner) == ("pictures-1", "pictures-2")
    assert from_a.owner != from_b.owner
    # The declaration itself was never bound.
    declared = app.registry.structure_registry.get_fullfilled_structure("@lib/thing")
    assert declared.injects == {"pictures": PictureClient}


def test_the_shrinker_defaults_to_the_objects_id() -> None:
    app = picture_app()
    app.register_structure(Thing, "@lib/thing", expand=expand_thing)

    structure = app.registry.structure_registry.get_fullfilled_structure("@lib/thing")
    assert structure.ashrink is not None


# ------------------------------------------------------------------ #
# What it refuses, and when                                          #
# ------------------------------------------------------------------ #


def test_a_lambda_is_refused_at_registration() -> None:
    """Annotation-driven injection means a lambda has nothing to read."""
    app = picture_app()

    with pytest.raises(StructureDefinitionError, match="is a lambda, which carries no"):
        app.register_structure(
            Thing, "@lib/thing", expand=lambda id, pictures: Thing(id, "x")
        )

    # Even one that needs nothing: the rule is the shape, not the arity.
    with pytest.raises(StructureDefinitionError, match="is a lambda, which carries no"):
        app.register_structure(Thing, "@lib/other", expand=lambda id: Thing(id, "x"))


def test_an_unannotated_parameter_is_refused_at_registration() -> None:
    app = picture_app()

    async def expand(id: str, pictures) -> Thing:  # noqa: ANN001
        """Says nothing about what it wants."""
        return Thing(id, "x")

    with pytest.raises(StructureDefinitionError, match="is unannotated"):
        app.register_structure(Thing, "@lib/thing", expand=expand)


def test_a_parameter_that_is_not_a_client_is_refused_at_registration() -> None:
    """Every parameter after the id is a client; a class no registered service
    returns is refused on the spot, long before anything connects."""
    app = picture_app()

    async def expand(id: str, depth: int) -> Thing:
        """Wants something no run can supply."""
        return Thing(id, "x")

    with pytest.raises(StructureDefinitionError, match="wants a int"):
        app.register_structure(Thing, "@lib/thing", expand=expand)


def test_a_client_no_registered_service_returns_is_refused_at_registration() -> None:
    """The service has to come first: it is what makes ``PictureClient`` a client."""
    app = bare_app()  # the pictures service exists, but this app never registered it

    with pytest.raises(StructureDefinitionError, match="no registered service returns one"):
        app.register_structure(Thing, "@lib/thing", expand=expand_thing)

    assert "@lib/thing" not in app.registry.structure_registry.identifier_structure_map


def test_the_refusal_names_the_structure_and_the_client() -> None:
    app = bare_app()

    with pytest.raises(StructureDefinitionError) as caught:
        app.register_structure(Thing, "@lib/thing", expand=expand_thing)

    message = str(caught.value)
    assert "@lib/thing" in message
    assert "PictureClient" in message


def test_registering_the_service_makes_it_valid() -> None:
    app = picture_app()
    app.register_structure(Thing, "@lib/thing", expand=expand_thing)

    snapshot = app.snapshot()
    assert "@lib/thing" in snapshot.registry.structure_registry.identifier_structure_map


def test_an_expander_that_wants_nothing_still_works() -> None:
    """The common case stays free: no injection, no copy at bind."""
    app = bare_app()

    async def expand(id: str) -> Thing:
        """No client needed."""
        return Thing(id, "nobody")

    app.register_structure(Thing, "@lib/thing", expand=expand)
    structure = app.registry.structure_registry.get_fullfilled_structure("@lib/thing")
    assert structure.injects == {}
    app.snapshot()
