"""Testing an app: its actions called for real, with no server.

An action is more than its function. Its arguments cross ports, it is handed
clients, a task and its states, and what it returns crosses the ports back.
Calling the function in a test checks none of that, and running it against a
deployment is not a unit test. :func:`local_app` runs the app for itself
instead: started as a run starts it, called through its own agent, with no
server anywhere::

    from arkitekt.testing import local_app
    from app import app, add

    def test_add():
        with local_app(app) as rt:
            assert rt.call_local(add, 1, 2) == 3

A test may hand the app a client in place of the one a service would build::

    with local_app(app, clients=[client]) as rt: ...

With pytest, the fixtures do the same for the project's own app. Load them in
``conftest.py``::

    pytest_plugins = ["arkitekt.testing"]

and a test asks for ``call``::

    def test_add(call):
        assert call("add", 1, 2) == 3

That is the unit suite, and where an app is tested. Whether it still works
against the real services is a second, small suite, run end to end on a runner
of its own: ``hub_call`` is ``call`` with the app connected to a hub made for
the test session from the images its services say host them (it needs Docker
and ``konstruktor``, and about a minute to start)::

    @pytest.mark.hub
    def test_it_stores_the_result(hub_call):
        assert hub_call("make_folder", name="results").name == "results"

``teststack`` is the whole of it in one typed fixture: the hub, the app, and the
app's run. Annotate it with the app's context (``None`` for an app without one)::

    @pytest.mark.hub
    def test_it_stores_the_result(teststack: TestStack[None]):
        folder = teststack.call("make_folder", name="results")
        assert teststack.runtime.require(Mikro).get_folder(folder.id).name == "results"

Nothing here is loaded unless a project asks for it, and nothing is autouse.
:func:`local_app` needs no pytest; the fixtures exist when it is installed.
"""

import os
import sys
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Generic, Optional

try:
    from arkitekt_runtime.local import LocalCallCancelledError, LocalCallError
except ImportError as e:  # pragma: no cover - depends on what is installed
    raise ImportError(
        "Testing an app calls its actions through the runtime, which is not installed: "
        "pip install 'arkitekt[rekuest]'."
    ) from e

from arkitekt.app.app import App, Ctx
from arkitekt.runtime import Runtime, _provider_for, connect_local

if TYPE_CHECKING:
    from konstruktor import Hub  # pyright: ignore[reportMissingImports]

#: The environment variable naming the app under test, as the CLI reads it.
TARGET_ENVVAR = "ARKITEKT_APP"


def local_app(
    app: App[Ctx],
    *,
    clients: Sequence[Any] = (),
    context: Optional[Ctx] = None,
) -> Runtime[Ctx]:
    """A run of ``app`` that reaches no server, to call its actions in.

    Entering it starts the app (startup hooks, states, background work); leaving
    it stops it (shutdown hooks). Use it as ``with`` or ``async with``.

    Args:
        app: The app under test.
        clients: What the app's actions are handed in place of the clients its
            services would build, matched by class, and entered and left with
            the run like them. A service that is not
            replaced builds its real client against an address that does not
            exist: there to be handed out, failing only if it is called through.
        context: The app context, for an app that declares one.

    Returns:
        The runtime, not yet entered. Call actions with
        :meth:`~arkitekt.runtime.Runtime.call_local` (``acall_local``,
        ``aiterate_local``).
    """
    return connect_local(app, clients=clients, context=context, offline=True)


@dataclass(frozen=True)
class TestStack(Generic[Ctx]):
    """The app under test, logged in to a hub made for the tests.

    What the ``teststack`` fixture hands a test. The parameter is the app's
    context, as it is of :class:`~arkitekt.App`: ``TestStack[Config]`` for an
    app declared with ``app_context=Config``, ``TestStack[None]`` for one
    without.
    """

    # Not a test class, whatever its name says to pytest.
    __test__ = False

    #: The hub, for the session: ``fakts_url``, ``redeem_token(name)``, ``logs()``.
    hub: "Hub"
    #: The app under test.
    app: App[Ctx]
    #: The app, started and logged in to the hub: ``runtime.require(Client)``.
    runtime: Runtime[Ctx]

    def call(self, action: Any, *args: Any, **kwargs: Any) -> Any:  # noqa: ANN401
        """Call one of the app's actions, with its services real: ``teststack.call("segment", image)``."""
        return self.runtime.call_local(action, *args, **kwargs)


class NoImageError(LookupError):
    """A service the app uses does not say which image hosts it."""


def service_images(app: App[Any]) -> list[str]:
    """The images that host what ``app`` needs of a deployment, in the order declared.

    Read off the services of a run of the app: its own, and the one its provider
    brings (an app that offers anything is served by rekuest). This is all a hub
    for the app's tests is made from.

    Raises:
        NoImageError: If a service that requires something of a deployment does
            not say which image hosts it (``@registry.service(image=...)``).
    """
    snapshot = app.snapshot(device_id=None, provider=_provider_for(app, required=False))
    images: list[str] = []
    for name, service in snapshot.services.items():
        if not service.get_requirements():
            continue
        image = getattr(service, "image", None)
        if image is None:
            raise NoImageError(
                f"The service '{name}' does not say which image hosts it, so no hub can be "
                f"made for it: declare it with `@registry.service(image=...)`."
            )
        if image not in images:
            images.append(image)
    return images


try:
    import pytest
except ImportError:  # pragma: no cover - depends on what is installed
    # `local_app` needs no test runner: the fixtures are for the one that is there.
    pytest = None  # type: ignore[assignment]

if pytest is not None:

    @pytest.fixture(scope="session")
    def arkitekt_app(pytestconfig: Any) -> App[Any]:  # noqa: ANN401 -- a pytest.Config
        """The project's app, found as the CLI finds it.

        ``$ARKITEKT_APP`` if set, else the module ``app`` in the directory pytest
        runs from. Override this fixture to test another app.
        """
        from arkitekt.cli.target import DEFAULT_TARGET, load_target

        root = str(pytestconfig.rootpath)
        if root not in sys.path:
            sys.path.insert(0, root)
        app, _, _ = load_target(os.environ.get(TARGET_ENVVAR) or DEFAULT_TARGET, root)
        return app


    @pytest.fixture()
    def arkitekt_clients() -> Sequence[Any]:
        """The clients the app's actions are handed in place of its services' own.

        Empty by default. A client is entered and left by the run, so hand out
        one that is not entered yet. To test against the real service, ask for
        ``hub_call`` instead.
        """
        return ()


    @pytest.fixture()
    def arkitekt_context() -> Any:  # noqa: ANN401
        """The app context the app under test is started with. Override it for an app that declares one."""
        return None


    @pytest.fixture()
    def local_runtime(
        arkitekt_app: App[Any],
        arkitekt_clients: Sequence[Any],
        arkitekt_context: Any,  # noqa: ANN401
    ) -> Iterator[Runtime[Any]]:
        """The app under test, started with no server, for the length of one test."""
        with local_app(arkitekt_app, clients=arkitekt_clients, context=arkitekt_context) as runtime:
            yield runtime


    @pytest.fixture()
    def call(local_runtime: Runtime[Any]) -> Callable[..., Any]:
        """Call one of the app's actions: ``call("add", 1, b=2)`` or ``call(add, 1, b=2)``."""
        return local_runtime.call_local


    def pytest_configure(config: Any) -> None:  # noqa: ANN401 -- a pytest.Config
        """Register the marker for tests that run against a hub."""
        config.addinivalue_line(
            "markers", "hub: end to end, against a hub made for the tests (needs Docker; not for the dev loop)."
        )


    @pytest.fixture(scope="session")
    def arkitekt_hub_apps() -> int:
        """How many apps log in to the hub: one redeem token serves one app.

        Eight by default: the app under test, and room for the others a test
        connects beside it (``arkitekt_hub.redeem_token("other")``).
        """
        return 8


    @pytest.fixture(scope="session")
    def arkitekt_hub(
        request: Any,  # noqa: ANN401 -- a pytest.FixtureRequest
        arkitekt_app: App[Any],
        arkitekt_hub_apps: int,
        tmp_path_factory: Any,  # noqa: ANN401 -- a pytest.TempPathFactory
    ) -> Iterator["Hub"]:
        """A hub of the app's own, for the session: the services it uses and a login for it.

        Made by konstruktor from the images the app's services declare
        (:func:`service_images`), on a port of its own, and removed afterwards.
        Tests that ask for it are skipped where no hub can be made.
        """
        # Installed, or this fixture would not exist: said again for the type checker,
        # which forgets it inside a function.
        import pytest

        try:
            import konstruktor
            from konstruktor.pytest_plugin import docker_available
        except ImportError:
            pytest.skip("A hub is made with konstruktor, which is not installed: pip install konstruktor.")
        if not hasattr(konstruktor, "testing_hub"):
            pytest.skip("A hub is made with konstruktor 0.17 or newer, and an older one is installed: pip install -U konstruktor.")
        if not docker_available():
            pytest.skip("A hub runs in Docker, which is not running here.")

        hub = request.getfixturevalue("konstruktor_hub")(
            service_images=service_images(arkitekt_app), redeem_tokens=arkitekt_hub_apps
        )
        with pytest.MonkeyPatch.context() as patch:
            # A hub has a new address on every run: its logins are this session's alone.
            patch.setenv("XDG_STATE_HOME", str(tmp_path_factory.mktemp("arkitekt-state")))
            # It has no mesh either, so there is none to look for.
            patch.setenv("ARKITEKT_MESH", "0")
            yield hub


    @pytest.fixture()
    def hub_runtime(
        arkitekt_app: App[Any],
        arkitekt_hub: "Hub",
        arkitekt_clients: Sequence[Any],
        arkitekt_context: Any,  # noqa: ANN401
    ) -> Iterator[Runtime[Any]]:
        """The app under test, started and logged in to its hub, for the length of one test.

        Its services are the real ones: ``hub_runtime.require(Mikro)`` is a client
        of the hub's mikro, and what an action is handed.
        """
        with connect_local(
            arkitekt_app,
            clients=arkitekt_clients,
            context=arkitekt_context,
            offline=False,
            url=arkitekt_hub.fakts_url,
            redeem_token=arkitekt_hub.redeem_token(arkitekt_app.identifier),
            headless=True,
        ) as runtime:
            yield runtime


    @pytest.fixture()
    def hub_call(hub_runtime: Runtime[Any]) -> Callable[..., Any]:
        """Call one of the app's actions, with its services real: ``hub_call("segment", image)``."""
        return hub_runtime.call_local


    @pytest.fixture()
    def teststack(
        arkitekt_app: App[Any],
        arkitekt_hub: "Hub",
        hub_runtime: Runtime[Any],
    ) -> TestStack[Any]:
        """The hub, the app under test and its run on that hub, for the length of one test.

        Annotate it with the app's context: ``teststack: TestStack[Config]``. The
        run is ``hub_runtime``'s own, so a test may ask for both.
        """
        return TestStack(hub=arkitekt_hub, app=arkitekt_app, runtime=hub_runtime)


__all__ = ["LocalCallCancelledError", "LocalCallError", "NoImageError", "TestStack", "local_app", "service_images"]
if pytest is not None:
    __all__ += [
        "arkitekt_app",
        "arkitekt_clients",
        "arkitekt_context",
        "arkitekt_hub",
        "arkitekt_hub_apps",
        "call",
        "hub_call",
        "hub_runtime",
        "local_runtime",
        "teststack",
    ]
