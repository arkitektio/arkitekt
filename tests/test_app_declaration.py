"""An App is a declaration: identity, clients and offerings, with no I/O.

The mechanisms it builds on (assembly, registry, snapshots) are arkitekt-spec's and
tested there. This checks what the app itself decides: which clients it uses, what
its manifest says, and that declaring never connects anything.
"""

import pytest
from arkitekt_spec.declare.definition.errors import DefinitionError

from arkitekt import App, AppDeclarationError, Bundle

from .fakes import BUILT, OtherClient, Picture, PictureClient


def test_declaring_builds_nothing() -> None:
    app = App("decl", clients=[PictureClient])

    assert app.clients() == [PictureClient]
    assert list(app.registry.clients) == ["pictures"]
    assert BUILT == []


def test_the_manifest_is_read_off_the_declaration() -> None:
    app = App(
        "com.test.decl",
        "1.2.3",
        scopes=["pictures_read"],
        logo="http://logo",
        clients=[PictureClient, OtherClient],
    )

    manifest = app.manifest
    assert (manifest.identifier, manifest.version, manifest.scopes, manifest.logo) == (
        "com.test.decl",
        "1.2.3",
        ["openid", "pictures_read"],
        "http://logo",
    )
    assert manifest.requirements is not None
    assert [r.key for r in manifest.requirements] == ["other", "pictures"]
    assert manifest.device_id is None, "the machine is the runtime's business"


def test_the_description_reaches_the_manifest() -> None:
    """What the app says it is travels to the agent through the manifest.

    The agent that provides an app is built from the manifest, and takes its
    description from here: the name identifies the agent, the description is
    what tells two of them apart in the UI. An app that declares none leaves it
    unset rather than blank, because the backend treats an omitted description
    as "keep what you have".
    """
    described = App("com.test.described", description="What this app is.")
    assert described.manifest.description == "What this app is."
    assert described.snapshot().manifest.description == "What this app is."

    assert App("com.test.plain").manifest.description is None


def test_the_identifier_defaults_to_the_declaring_file() -> None:
    assert App().identifier == "test_app_declaration"


def test_a_script_that_offers_nothing_uses_no_rekuest() -> None:
    app = App("script", clients=[PictureClient])
    assert "rekuest" not in app.registry.clients
    assert app.provider is None and app.registry.provider is None


def test_offering_anything_uses_no_client_of_its_own() -> None:
    app = App("offers")

    @app.action
    def double(x: int) -> int:
        """Doubles."""
        return x * 2

    assert app.registry.clients == {} and app.registry.provider is None, (
        "the app declares what it offers; run() serves it through rekuest"
    )


def test_an_annotation_naming_a_client_brings_it_and_is_injected() -> None:
    """A ``@client`` class, or a ``@structure`` its client owns, is enough: nothing is registered."""
    app = App("inject")

    @app.action
    def show(
        picture: Picture, pictures: PictureClient, other: OtherClient | None
    ) -> str:
        """Shows it."""
        return picture.id

    assert list(app.registry.clients) == ["pictures", "other"]
    assert app.registry.structure_registry.is_client(PictureClient)
    ports = [port.key for port in app.registry.implementations["show"].definition.args]
    assert ports == ["picture"], "clients are injected, not ports"


def test_an_unmarked_class_in_a_port_is_refused_at_assembly() -> None:
    class Unmarked:
        pass

    app = App("no-infer")

    @app.action
    def show(thing: Unmarked) -> str:
        """Wants a class nothing declares."""
        return "x"

    with pytest.raises(AppDeclarationError) as refused:
        app.declaration()
    assert refused.group_contains(DefinitionError, match="Unmarked")


def test_using_a_client_twice_is_harmless() -> None:
    app = App("twice", clients=[PictureClient])
    app.register_client(PictureClient, PictureClient)
    assert app.clients() == [PictureClient]


def test_only_a_client_class_is_a_client_and_only_a_provider_a_provider() -> None:
    with pytest.raises(TypeError, match="is not a client"):
        App("class", clients=[Picture])
    with pytest.raises(TypeError, match="is not a provider"):
        # The wrong type is the point.
        App("provider", provider=PictureClient)  # pyright: ignore[reportArgumentType]


def test_a_registered_action_is_still_callable_as_itself() -> None:
    app = App("callable")

    @app.action
    def owner(picture: Picture, pictures: PictureClient) -> str:
        """Who has it."""
        return f"{picture.id}@{pictures.name}"

    assert owner(Picture("1", "x"), pictures=PictureClient("local")) == "1@local"


def test_snapshot_validates_without_connecting() -> None:
    app = App("inspect")

    @app.action
    def show(picture: Picture) -> str:
        """Shows it."""
        return picture.id

    snapshot = app.snapshot()
    assert "show" in snapshot.registry.implementations
    assert snapshot.clients == app.registry.clients
    assert BUILT == []


def test_requirements_come_only_from_clients() -> None:
    app = App("clients-only", clients=[PictureClient])

    assert [r.key for r in app.requirements] == ["pictures"]
    assert not hasattr(app, "require")


def test_an_app_offers_what_it_includes() -> None:
    extras = Bundle()

    def snap(x: int) -> int:
        """Takes a picture."""
        return x

    extras.register_action(snap)
    app = App("microscope", "1", include=[extras])

    assert "snap" in app.registry.implementations
    assert app.interfaces == ["snap"]


def test_declare_puts_the_protocol_on_the_apps_own_registry() -> None:
    from typing import Protocol

    app = App("decl")

    @app.declare(app="lab")
    class Lab(Protocol):
        def ping(self, n: int) -> int:
            """Ping."""
            ...

    assert app.registry.structure_registry.is_protocol(Lab)
    assert "rekuest" not in app.registry.clients, (
        "run() brings rekuest, not the declaration"
    )
    assert not any(name.startswith("__rekuest") for name in vars(Lab))


class Config:
    pass


def test_an_app_declares_its_context_class_on_its_registry() -> None:
    app = App("ctx", app_context=Config)
    assert app.app_context is Config
    assert app.registry.structure_registry.app_contexts == {Config: "Config"}
    assert App("bare").app_context is None
    assert not callable(App("bare").app_context), "a property now, not a decorator"


def test_a_workflow_is_offered_like_an_action_and_may_call_other_apps() -> None:
    from typing import Protocol

    from arkitekt import Effects, Execution

    app = App("orchestrator", effects=Effects.IRREVERSIBLE)

    @app.declare(app="lab")
    class Lab(Protocol):
        def ping(self, n: int) -> int:
            """Ping."""
            ...

    @app.workflow
    def twice(lab: Lab, n: int) -> int:
        """Ping twice."""
        return lab.ping(lab.ping(n))

    @app.action(effects=Effects.NONE)
    def local(n: int) -> int:
        """Local."""
        return n

    implementations = app.registry.implementations
    assert implementations["twice"].execution == Execution.WORKFLOW
    # The app's default for what doesn't say; an action's own claim wins.
    assert implementations["twice"].effects == Effects.IRREVERSIBLE
    assert (implementations["local"].execution, implementations["local"].effects) == (
        Execution.PLAIN,
        Effects.NONE,
    )


def test_a_plain_action_calling_another_app_is_refused() -> None:
    from typing import Protocol

    app = App("plain")

    @app.declare(app="lab")
    class Lab(Protocol):
        def ping(self, n: int) -> int:
            """Ping."""
            ...

    @app.action
    def calls(lab: Lab, n: int) -> int:
        """Calls the lab."""
        return lab.ping(n)

    with pytest.raises(AppDeclarationError) as refused:
        app.declaration()
    assert refused.group_contains(DefinitionError, match="@app.workflow")


def test_a_named_return_is_read_by_its_key() -> None:
    from typing import Annotated

    from arkitekt import Key

    app = App("named")

    @app.action
    def count(values: list[int]) -> Annotated[int, Key("count")]:
        """Count"""
        return len(values)

    assert [
        port.key for port in app.registry.implementations["count"].definition.returns
    ] == ["count"]
