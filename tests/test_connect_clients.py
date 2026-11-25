"""``connect(Mikro, ...)``: a script's clients, connected through the offline fakts."""

import pytest

from arkitekt import App, connect

from .fakes import BUILT, OtherClient, PictureClient


def test_one_class_yields_the_client() -> None:
    with connect(PictureClient) as picture:
        assert picture is BUILT[-1]


def test_several_classes_yield_a_tuple_in_order() -> None:
    with connect(OtherClient, PictureClient) as (other, picture):
        assert (other.name, picture.name) == ("other", "pictures-1")


def test_the_identifier_defaults_to_the_calling_file() -> None:
    assert connect(PictureClient).app.identifier == "test_connect_clients"
    assert connect(PictureClient, identifier="x").app.identifier == "x"


def test_script_and_app_forms_do_not_mix() -> None:
    with pytest.raises(TypeError, match="connects a script's clients"):
        connect(PictureClient, provide=True)  # pyright: ignore[reportCallIssue]
    with pytest.raises(TypeError, match="takes one app"):
        connect(App("app"), PictureClient)  # pyright: ignore[reportCallIssue]
