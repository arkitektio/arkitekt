"""A hand-registered structure whose expander asks for clients by annotation.

The ``@structure`` path is the spec's and tested there. This is the other one: a
type a shared library defines, fetched back through a client the run supplies.
"""

import pytest
from arkitekt_spec.declare.structures.errors import StructureDefinitionError
from arkitekt_spec.declare.structures.types import FullFilledStructure

from arkitekt import App, AppDeclarationError, connect
from arkitekt.runtime import Runtime

from .fakes import PictureClient, fake_provider


class Thing:
    """A type a shared library defines, fetched through someone else's client."""

    def __init__(self, id: str, owner: str) -> None:
        self.id = id
        self.owner = owner


async def expand_thing(id: str, pictures: PictureClient) -> Thing:
    """Fetch a Thing by id, through the run's pictures client."""
    return Thing(id, pictures.name)


def picture_app() -> App[None]:
    """An app with a fake rekuest; its expanders bring the clients they ask for."""
    return App("structures", provider=fake_provider())


def refused(app: App[None]) -> pytest.ExceptionInfo[AppDeclarationError]:
    """What assembling ``app`` raises."""
    with pytest.raises(AppDeclarationError) as caught:
        app.declaration()
    return caught


# ------------------------------------------------------------------ #
# What it buys                                                       #
# ------------------------------------------------------------------ #


@pytest.mark.asyncio
async def test_an_expander_is_handed_the_runs_client() -> None:
    app = picture_app()
    app.register_structure(Thing, "@lib/thing", expand=expand_thing)

    async with connect(app) as rt:
        assert rt.snapshot is not None
        structure = rt.snapshot.registry.structure_registry.get_fullfilled_structure(
            "@lib/thing"
        )
        thing = await structure.expand("1")

    assert isinstance(thing, Thing), "expand() returns an opaque object"
    assert (thing.id, thing.owner) == ("1", rt.require(PictureClient).name)


@pytest.mark.asyncio
async def test_each_run_expands_through_its_own_client() -> None:
    """The per-run isolation `bind` exists to protect, for injected expanders too."""
    app = picture_app()
    app.register_structure(Thing, "@lib/thing", expand=expand_thing)

    def structure_of(rt: Runtime[None]) -> FullFilledStructure:
        assert rt.snapshot is not None, "an entered run has its snapshot"
        return rt.snapshot.registry.structure_registry.get_fullfilled_structure(
            "@lib/thing"
        )

    async with connect(app) as a:
        async with connect(app) as b:
            from_a = await structure_of(a).expand("1")
            from_b = await structure_of(b).expand("2")

    assert isinstance(from_a, Thing), "expand() returns an opaque object"
    assert isinstance(from_b, Thing)
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


def test_a_lambda_is_refused_at_assembly() -> None:
    """Annotation-driven injection means a lambda has nothing to read."""
    # Even one that needs nothing: the rule is the shape, not the arity.
    for expand in (lambda id, pictures: Thing(id, "x"), lambda id: Thing(id, "x")):
        app = picture_app()
        app.register_structure(Thing, "@lib/thing", expand=expand)
        assert refused(app).group_contains(
            StructureDefinitionError, match="is a lambda, which carries no"
        )


def test_an_unannotated_parameter_is_refused_at_assembly() -> None:
    app = picture_app()

    async def expand(id: str, pictures) -> Thing:  # noqa: ANN001 -- the missing annotation is the case
        """Says nothing about what it wants."""
        return Thing(id, "x")

    app.register_structure(Thing, "@lib/thing", expand=expand)
    assert refused(app).group_contains(StructureDefinitionError, match="is unannotated")


def test_a_parameter_that_is_not_a_client_is_refused_at_assembly() -> None:
    """Every parameter after the id is a client; a class that is no ``@client`` is
    refused when the app is assembled, long before anything connects."""
    app = picture_app()

    async def expand(id: str, depth: int) -> Thing:
        """Wants something no run can supply."""
        return Thing(id, "x")

    app.register_structure(Thing, "@lib/thing", expand=expand)
    caught = refused(app)
    assert caught.group_contains(StructureDefinitionError, match="wants a int")
    assert "@lib/thing" in str(caught.value)


def test_an_expander_asking_for_a_client_brings_it() -> None:
    """The client need not be named anywhere else: the expander's annotation is enough."""
    app = App("structures")
    app.register_structure(Thing, "@lib/thing", expand=expand_thing)

    snapshot = app.snapshot()
    assert "@lib/thing" in snapshot.registry.structure_registry.identifier_structure_map
    assert list(snapshot.clients) == ["pictures"]


def test_an_expander_that_wants_nothing_still_works() -> None:
    """The common case stays free: no injection, no copy at bind."""
    app = App("structures")

    async def expand(id: str) -> Thing:
        """No client needed."""
        return Thing(id, "nobody")

    app.register_structure(Thing, "@lib/thing", expand=expand)
    structure = app.registry.structure_registry.get_fullfilled_structure("@lib/thing")
    assert structure.injects == {}
    app.snapshot()
