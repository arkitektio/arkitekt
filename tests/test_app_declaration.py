"""An App is a declaration: identity, services and offerings, with no I/O.

The mechanisms it builds on (registry, snapshots) are rekuest's and tested there.
This checks what the app itself decides: which services it uses, what its
manifest says, and that declaring never connects anything.
"""

from typing import Optional

import pytest
from arkitekt_spec.declare.definition.errors import DefinitionError
from arkitekt_spec.declare.structures.errors import StructureRegistryError

from arkitekt import App

from .fakes import OtherClient, OtherService, Picture, PictureClient, PictureService


def test_declaring_builds_nothing() -> None:
    built: list = []
    app = App("decl", services=[PictureService(built)])

    assert app.services == ["pictures"]
    assert built == []


def test_the_manifest_is_read_off_the_declaration() -> None:
    app = App(
        "com.test.decl",
        "1.2.3",
        scopes=["read"],
        logo="http://logo",
        services=[PictureService(), OtherService()],
    )

    manifest = app.manifest
    assert (manifest.identifier, manifest.version, manifest.scopes, manifest.logo) == (
        "com.test.decl",
        "1.2.3",
        ["read"],
        "http://logo",
    )
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
    app = App("script", services=[PictureService()])
    assert "rekuest" not in app.services
    assert not app.registry.providers


def test_offering_anything_declares_no_service_of_its_own() -> None:
    app = App("offers")

    @app.action
    def double(x: int) -> int:
        """Doubles."""
        return x * 2

    assert app.services == [] and not app.registry.providers, (
        "the app declares what it offers; run() serves it through rekuest"
    )


def test_a_registered_services_client_is_injected_not_a_port() -> None:
    app = App("inject", services=[PictureService(), OtherService()])

    @app.action
    def show(picture: Picture, pictures: PictureClient, other: Optional[OtherClient]) -> str:
        """Shows it."""
        return picture.id

    assert app.services == ["pictures", "other"]
    assert app.registry.structure_registry.is_client(PictureClient)
    ports = [port.key for port in app.registry.implementations["show"].definition.args]
    assert ports == ["picture"], "clients are injected, not ports"


def test_a_client_no_registered_service_returns_is_a_port_and_is_refused() -> None:
    """Nothing is inferred: without its service, ``OtherClient`` is just an
    unregistered class in a port, and registration says to register the service."""
    app = App("no-infer", services=[PictureService()])

    with pytest.raises(Exception, match="register the service"):

        @app.action
        def show(picture: Picture, other: OtherClient) -> str:
            """Wants a client the app never registered."""
            return picture.id

    assert "show" not in app.registry.implementations


def test_a_structure_port_alone_infers_nothing_and_says_what_to_declare() -> None:
    app = App("no-infer")

    with pytest.raises(DefinitionError):

        @app.action
        def show(picture: Picture) -> str:
            """Shows it."""
            return picture.id


def test_registering_a_service_twice_is_harmless() -> None:
    pictures = PictureService()
    app = App("twice", services=[pictures])
    app.service(pictures).service(pictures)
    assert app.services == ["pictures"]


def test_two_services_of_one_name_are_refused() -> None:
    with pytest.raises(ValueError, match="both named 'pictures'"):
        App("clash", services=[PictureService(), PictureService()])


def test_a_client_class_is_not_a_service() -> None:
    """There is no catalog to look a class up in: the service object is passed."""
    with pytest.raises(TypeError, match="PictureClient is not a service"):
        App("class", services=[PictureClient])  # type: ignore[list-item]
    with pytest.raises(TypeError, match="is not a service"):
        App("name", services=["pictures"])  # type: ignore[list-item]


def test_a_registered_action_is_still_callable_as_itself() -> None:
    app = App("callable", services=[PictureService()])

    @app.action
    def owner(picture: Picture, pictures: PictureClient) -> str:
        """Who has it."""
        return f"{picture.id}@{pictures.name}"

    assert owner(Picture("1", "x"), pictures=PictureClient("local")) == "1@local"


def test_snapshot_validates_without_connecting() -> None:
    built: list = []
    app = App("inspect", services=[PictureService(built)])

    @app.action
    def show(picture: Picture) -> str:
        """Shows it."""
        return picture.id

    snapshot = app.snapshot()
    assert "show" in snapshot.registry.implementations
    assert snapshot.services == app.service_builders
    assert built == []


def test_snapshot_refuses_a_port_the_app_cannot_resolve() -> None:
    app = App("broken", services=[PictureService()])

    @app.action
    def show(picture: Picture) -> str:
        """Shows it."""
        return picture.id

    # The service's structures leave the registry: the port now names nothing.
    del app.registry.structure_registry.identifier_structure_map["@pictures/picture"]
    with pytest.raises(StructureRegistryError, match="services="):
        app.snapshot()


def test_requirements_come_only_from_services() -> None:
    app = App("services-only", services=[PictureService()])

    assert [r.key for r in app.requirements] == ["pictures"]
    assert not hasattr(app, "require")


def test_declare_puts_the_protocol_on_the_apps_own_registry() -> None:
    from typing import Protocol

    app = App("decl")

    @app.declare(app="lab")
    class Lab(Protocol):
        def ping(self, n: int) -> int:
            """Ping."""
            ...

    assert app.registry.structure_registry.is_protocol(Lab)
    assert "rekuest" not in app.services, "run() brings rekuest, not the declaration"
    assert not any(name.startswith("__rekuest") for name in vars(Lab))


class Config:
    pass


def test_an_app_declares_its_context_class_on_its_registry() -> None:
    app = App("ctx", app_context=Config)
    assert app.app_context is Config
    assert app.registry.structure_registry.app_contexts == {Config: "Config"}
    assert App("bare").app_context is None
    assert not callable(App("bare").app_context), "a property now, not a decorator"


def test_an_app_over_a_declaring_registry_reports_its_context() -> None:
    from arkitekt_spec.declare.app import AppRegistry

    registry = AppRegistry()
    registry.app_context(Config)
    assert App("over", registry=registry).app_context is Config
