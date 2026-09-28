"""easy/aeasy/interactive: App + connect, handing back the named clients in order.

The pieces (App, Runtime, connect) are tested on their own; this checks only what
the shortcuts add: which app they declare, what they yield, and that each entry
gets its own runtime. Runs resolve through the offline fakts every test gets.
"""

from typing import Any

import pytest

from arkitekt import App, Easy, aeasy, easy, interactive
from arkitekt import shortcuts

from .fakes import OtherClient, OtherService, PictureClient, PictureService


def options() -> dict[str, Any]:
    """Extra options every shortcut call here passes: none, today."""
    return {}


BUILT: list[PictureClient] = []
PICTURES, OTHER = PictureService(BUILT), OtherService()


def test_a_client_class_is_refused_where_a_service_is_expected() -> None:
    with pytest.raises(TypeError, match="is not a service"):
        # The wrong type is the point.
        easy("class", PictureClient, **options())  # pyright: ignore[reportArgumentType]


def test_easy_declares_an_app_and_connects_nothing() -> None:
    shortcut = easy("shortcut", PICTURES, OTHER, version="1.2.0", **options())

    assert isinstance(shortcut, Easy)
    assert isinstance(shortcut.app, App)
    assert (shortcut.app.identifier, shortcut.app.version) == ("shortcut", "1.2.0")
    assert shortcut.app.services == ["pictures", "other"]


def test_several_clients_come_back_in_order() -> None:
    with easy("order", OTHER, PICTURES) as (other, picture):
        assert isinstance(other, OtherClient)
        assert picture is BUILT[-1], "the client the pictures builder just made"


def test_one_client_comes_back_bare_and_none_as_none() -> None:
    with easy("one", PICTURES, **options()) as picture:
        assert isinstance(picture, PictureClient)
    with easy("none", **options()) as nothing:
        assert nothing is None


@pytest.mark.asyncio
async def test_aeasy_yields_the_same_for_async_with() -> None:
    async with aeasy("async", PICTURES, OTHER, **options()) as (picture, other):
        assert (isinstance(picture, PictureClient), other.name) == (True, "other")


def test_each_entry_gets_its_own_runtime() -> None:
    shortcut = easy("twice", PICTURES, **options())
    assert shortcut.runtime() is not shortcut.runtime()

    with shortcut:
        with shortcut:
            assert len(shortcut._runtimes) == 2
            inner, outer = shortcut._runtimes[1], shortcut._runtimes[0]
            assert inner is not outer
    assert shortcut._runtimes == []


def test_connection_options_reach_the_runtime_not_the_app() -> None:
    shortcut = easy("opts", PICTURES, url="http://x", force=True, device_id="n", **options())
    runtime = shortcut.runtime()
    assert (runtime.options.url, runtime.options.force, runtime.options.device_id) == (
        "http://x",
        True,
        "n",
    )


def test_an_unknown_option_is_refused() -> None:
    with pytest.raises(TypeError, match="unexpected keyword argument"):
        # The unknown option is the point.
        easy("bad", PICTURES, colour="blue", **options())  # pyright: ignore[reportCallIssue]


def test_the_identifier_defaults_to_the_calling_file() -> None:
    assert easy(None, **options()).app.identifier == "test_shortcuts"


def test_interactive_stays_connected_until_exit() -> None:
    log: list[str] = []
    picture = interactive("notebook", PictureService(log=log))

    assert isinstance(picture, PictureClient) and log == ["enter pictures-1"]
    shortcuts._leave_interactive()
    assert log == ["enter pictures-1", "exit pictures-1"]


def test_interactive_holds_one_runtime_per_app() -> None:
    """A re-run notebook cell must not pile up connections."""
    log: list[str] = []
    service = PictureService(log=log)
    interactive("notebook", service)
    interactive("notebook", service)

    assert log == ["enter pictures-1", "exit pictures-1", "enter pictures-2"]
    assert list(shortcuts._interactive_runtimes) == ["notebook"]
    shortcuts._leave_interactive()
    assert log[-1] == "exit pictures-2"


def test_the_runtime_configures_no_logging() -> None:
    """A library that reconfigures root logging behind the caller's back is a nuisance."""
    with pytest.raises(TypeError):
        # There is no such option any more; that is the point.
        easy("x", log_level="DEBUG", **options())  # pyright: ignore[reportCallIssue]
