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

On a hub, a call goes to the app's agent in-process by default: the services are
real, the server that assigns tasks is not asked. Set
``ARKITEKT_CALL_THROUGH_REKUEST=1`` (or override the ``arkitekt_call_through_rekuest``
fixture) and the app registers with the hub's rekuest and is served, and every
``teststack.call`` / ``hub_call`` is a task rekuest assigns to it, as another app's
call would be: same tests, the whole path.

Nothing here is loaded unless a project asks for it, and nothing is autouse.
:func:`local_app` needs no pytest; the fixtures exist when it is installed.
"""

import os
import sys
import threading
import time
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Generic, Optional, cast

try:
    from arkitekt_runtime.local import LocalCallCancelledError, LocalCallError
except ImportError as e:  # pragma: no cover - depends on what is installed
    raise ImportError(
        "Testing an app calls its actions through the runtime, which is not installed: "
        "pip install 'arkitekt[rekuest]'."
    ) from e

from arkitekt.app.app import App, Ctx
from arkitekt.runtime import ConnectionState, Runtime, _interface_of, _provider_for, connect, connect_local

if TYPE_CHECKING:
    from konstruktor import Hub  # pyright: ignore[reportMissingImports]

#: The environment variable naming the app under test, as the CLI reads it.
TARGET_ENVVAR = "ARKITEKT_APP"
#: The environment variable that sends a hub test's calls through the hub's rekuest.
THROUGH_REKUEST_ENVVAR = "ARKITEKT_CALL_THROUGH_REKUEST"
#: How long a run served for a test may take to register with rekuest, in seconds.
REGISTRATION_TIMEOUT = 120.0


def call_through_rekuest_requested() -> bool:
    """Whether ``$ARKITEKT_CALL_THROUGH_REKUEST`` asks for calls through rekuest (1, true, yes, on)."""
    return os.environ.get(THROUGH_REKUEST_ENVVAR, "").strip().lower() in ("1", "true", "yes", "on")


def call_through_rekuest(runtime: Runtime[Any], action: Any, *args: Any, **kwargs: Any) -> Any:  # noqa: ANN401
    """Call one of the app's own actions as a task rekuest assigns to it, and return its result.

    ``runtime`` is a run of the app that provides it (``connect(app, provide=True)``,
    running): the call is a root task on the app's own implementation, made with the
    AUTO policy, since nobody is there to approve what it asks for.
    """
    from arkitekt_runtime.types import TaskPolicy
    from rekuest.client.client import Rekuest

    agent = runtime.agent
    if agent is None:
        raise LookupError("Only a run that provides the app is called through rekuest: `connect(app, provide=True)`.")
    rekuest = runtime.require(Rekuest)
    implementation = rekuest.my_implementation_at(interface=_interface_of(agent, action))
    return rekuest.call(implementation, *args, policy=TaskPolicy.AUTO, **kwargs)


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


@contextmanager
def served_app(
    app: App[Ctx],
    *,
    url: str,
    mandate_key: str,
    context: Optional[Ctx] = None,
    timeout: float = REGISTRATION_TIMEOUT,
) -> Iterator[Runtime[Ctx]]:
    """``app`` logged in at ``url``, registered with its rekuest and served, until the block is left.

    What a hub test runs through rekuest is made of: entered, the app is a real agent
    rekuest assigns tasks to (:func:`call_through_rekuest`), and its services are the
    real ones (``runtime.require(Mikro)``).

    Raises:
        TimeoutError: If it does not register within ``timeout`` seconds.
        RuntimeError: If its run stops before it registers (or what stopped it).
    """
    registered = threading.Event()

    async def on_state(state: ConnectionState) -> None:
        if state is ConnectionState.REGISTERED:
            registered.set()

    with connect(
        app, provide=True, url=url, mandate_key=mandate_key, headless=True, connection_listener=on_state
    ) as runtime:
        # None is the context of an app that declares none; run_detached checks it against the app.
        running = runtime.run_detached(cast(Ctx, context))
        try:
            deadline = time.monotonic() + timeout
            while not registered.wait(0.5):
                if running.done():
                    running.result()  # raises what stopped it
                    raise RuntimeError("The app's run stopped before it registered with rekuest.")
                if time.monotonic() > deadline:
                    raise TimeoutError(f"The app did not register with rekuest within {timeout:.0f}s.")
            yield runtime
        finally:
            running.cancel()


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

    #: The hub, for the session: ``fakts_url``, ``mandate_key(name)``, ``logs()``.
    hub: "Hub"
    #: The app under test.
    app: App[Ctx]
    #: The app, started and logged in to the hub: ``runtime.require(Client)``.
    runtime: Runtime[Ctx]
    #: Whether :meth:`call` goes through the hub's rekuest rather than to the agent in-process.
    through_rekuest: bool = False

    def call(self, action: Any, *args: Any, **kwargs: Any) -> Any:  # noqa: ANN401
        """Call one of the app's actions, with its services real: ``teststack.call("segment", image)``."""
        if self.through_rekuest:
            return call_through_rekuest(self.runtime, action, *args, **kwargs)
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
        """How many apps log in to the hub: one mandate key serves one app.

        Eight by default: the app under test, and room for the others a test
        connects beside it (``arkitekt_hub.mandate_key("other")``).
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
            service_images=service_images(arkitekt_app), mandate_keys=arkitekt_hub_apps
        )
        with pytest.MonkeyPatch.context() as patch:
            # A hub has a new address on every run: its logins are this session's alone.
            patch.setenv("XDG_STATE_HOME", str(tmp_path_factory.mktemp("arkitekt-state")))
            # It has no mesh either, so there is none to look for.
            patch.setenv("ARKITEKT_MESH", "0")
            yield hub


    @pytest.fixture(scope="session")
    def arkitekt_call_through_rekuest() -> bool:
        """Whether a hub test's calls are tasks the hub's rekuest assigns, rather than in-process calls.

        ``$ARKITEKT_CALL_THROUGH_REKUEST`` by default (see
        :func:`call_through_rekuest_requested`); override it to pin a suite to one way.
        """
        return call_through_rekuest_requested()


    @pytest.fixture()
    def hub_runtime(
        arkitekt_app: App[Any],
        arkitekt_hub: "Hub",
        arkitekt_clients: Sequence[Any],
        arkitekt_context: Any,  # noqa: ANN401
        arkitekt_call_through_rekuest: bool,
    ) -> Iterator[Runtime[Any]]:
        """The app under test, started and logged in to its hub, for the length of one test.

        Its services are the real ones: ``hub_runtime.require(Mikro)`` is a client
        of the hub's mikro, and what an action is handed. Through rekuest, the app
        is also registered with the hub's rekuest and served until the test ends.
        """
        url = arkitekt_hub.fakts_url
        mandate_key = arkitekt_hub.mandate_key(arkitekt_app.identifier)
        if not arkitekt_call_through_rekuest:
            with connect_local(
                arkitekt_app,
                clients=arkitekt_clients,
                context=arkitekt_context,
                offline=False,
                url=url,
                mandate_key=mandate_key,
                headless=True,
            ) as runtime:
                yield runtime
            return

        if arkitekt_clients:
            raise ValueError(
                "`arkitekt_clients` replaces services in an in-process run only: called through "
                "rekuest, the app is a real agent and is handed its real services. Unset "
                f"${THROUGH_REKUEST_ENVVAR} for this suite, or drop the replacement clients."
            )
        with served_app(arkitekt_app, url=url, mandate_key=mandate_key, context=arkitekt_context) as runtime:
            yield runtime


    @pytest.fixture()
    def hub_call(hub_runtime: Runtime[Any], arkitekt_call_through_rekuest: bool) -> Callable[..., Any]:
        """Call one of the app's actions, with its services real: ``hub_call("segment", image)``."""
        if arkitekt_call_through_rekuest:
            return lambda action, *args, **kwargs: call_through_rekuest(hub_runtime, action, *args, **kwargs)
        return hub_runtime.call_local


    @pytest.fixture()
    def teststack(
        arkitekt_app: App[Any],
        arkitekt_hub: "Hub",
        hub_runtime: Runtime[Any],
        arkitekt_call_through_rekuest: bool,
    ) -> TestStack[Any]:
        """The hub, the app under test and its run on that hub, for the length of one test.

        Annotate it with the app's context: ``teststack: TestStack[Config]``. The
        run is ``hub_runtime``'s own, so a test may ask for both.
        """
        return TestStack(
            hub=arkitekt_hub,
            app=arkitekt_app,
            runtime=hub_runtime,
            through_rekuest=arkitekt_call_through_rekuest,
        )


__all__ = [
    "THROUGH_REKUEST_ENVVAR",
    "LocalCallCancelledError",
    "LocalCallError",
    "NoImageError",
    "TestStack",
    "call_through_rekuest",
    "call_through_rekuest_requested",
    "local_app",
    "served_app",
    "service_images",
]
if pytest is not None:
    __all__ += [
        "arkitekt_app",
        "arkitekt_call_through_rekuest",
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
