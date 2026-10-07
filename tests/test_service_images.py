"""What a hub for an app's tests is made from: the images its services say host them."""

from typing import Annotated

import pytest
from arkitekt_spec.declare.app import AppRegistry
from fakts import Alias, Require

from arkitekt import App
from arkitekt.testing import NoImageError, service_images


class Client:
    pass


class OtherClient:
    pass


def hosted(image: str | None = "example/pictures:3"):  # noqa: ANN201 -- a Service
    registry = AppRegistry()

    @registry.service(image=image)
    def pictures(pictures: Annotated[Alias, Require("live.test.pictures")]) -> Client:
        """Pictures, for tests."""
        return Client()

    return pictures


def test_an_apps_services_name_the_images_of_its_hub() -> None:
    assert service_images(App("images", "0.1.0", services=[hosted()])) == ["example/pictures:3"]


def test_an_app_that_offers_something_needs_what_serves_it_too() -> None:
    """The provider's service is part of the app a run logs in as, so of its hub."""
    rekuest = pytest.importorskip("rekuest.arkitekt")
    app = App("images", "0.1.0", services=[hosted()])

    @app.action
    def add(a: int, b: int) -> int:
        """Add"""
        return a + b

    assert service_images(app) == ["example/pictures:3", rekuest.rekuest.image]


def test_a_service_without_an_image_is_named() -> None:
    with pytest.raises(NoImageError, match="'pictures'"):
        service_images(App("images", "0.1.0", services=[hosted(image=None)]))


def test_a_service_that_requires_nothing_needs_no_image() -> None:
    registry = AppRegistry()

    @registry.service()
    def other() -> OtherClient:
        """Needs no deployment."""
        return OtherClient()

    assert service_images(App("images", "0.1.0", services=[other])) == []
