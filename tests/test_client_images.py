"""What a hub for an app's tests is made from: the images its clients say host their servers."""

from typing import Annotated, Self

import pytest
from fakts import Alias, Require

from arkitekt import App, client
from arkitekt.testing import NoImageError, client_images


@client(image="example/pictures:3")
class Hosted:
    @classmethod
    def from_fakts(
        cls, pictures: Annotated[Alias, Require("live.test.pictures")]
    ) -> Self:
        return cls()


@client()
class Unhosted:
    @classmethod
    def from_fakts(cls, other: Annotated[Alias, Require("live.test.other")]) -> Self:
        return cls()


@client(requires={})
class Local:
    """Needs no deployment."""


def test_an_apps_clients_name_the_images_of_its_hub() -> None:
    assert client_images(App("images", "0.1.0", clients=[Hosted])) == [
        "example/pictures:3"
    ]


def test_an_app_that_offers_something_needs_what_serves_it_too() -> None:
    """The provider's client is part of the app a run logs in as, so of its hub."""
    pytest.importorskip("rekuest.arkitekt")
    from arkitekt_spec.declare.client import client_of
    from rekuest.client.client import Rekuest

    app = App("images", "0.1.0", clients=[Hosted])

    @app.action
    def add(a: int, b: int) -> int:
        """Add"""
        return a + b

    rekuest = client_of(Rekuest)
    assert rekuest is not None
    assert client_images(app) == ["example/pictures:3", rekuest.image]


def test_a_client_without_an_image_is_named() -> None:
    with pytest.raises(NoImageError, match="'unhosted'"):
        client_images(App("images", "0.1.0", clients=[Unhosted]))


def test_a_client_that_requires_nothing_needs_no_image() -> None:
    assert client_images(App("images", "0.1.0", clients=[Local])) == []
