"""The Qt app: a declaration whose actions may run in, or talk to, the Qt event loop."""

from typing import Any, Callable, Dict, List, Optional, ParamSpec, Sequence, TypeVar, overload

from fakts.models import PublicSource
from koil import run_threaded
from koil.qt import async_to_qt
from rekuest.actors.types import Actifier
from rekuest.api.schema import AssignWidgetInput
from rekuest.app import AppRegistry
from rekuest.register import WrappedFunction

from arkitekt.app.app import App, Ctx, _caller_module_name
from rekuest.service import Service

R = TypeVar("R")
P = ParamSpec("P")


class QtApp(App[Ctx]):
    """An app whose actions may run in the Qt event loop.

    A declaration like every app: a widget registers on it in its constructor
    (``app.action``, ``app.register_in_qt_loop``, ...), and a
    :class:`~arkitekt.qt.MagicBar` runs it, through a runtime::

        app = QtApp("my-viewer", parent=window)
        bar = MagicBar(connect(app))

    Args:
        identifier: The app's globally unique identifier. Defaults to the name of
            the file that constructs it.
        version: The app's version.
        parent: The Qt object that owns what :meth:`wrap` creates.
        logo: A public http url of the app's logo.
        scopes: The scopes the app requests. Defaults to ``["openid"]``.
        author: Who wrote the app.
        public_sources: Public sources the app announces in its manifest.
        services: The services the app uses (``[mikro_service]``).
        registry: The registry to declare into. A fresh one by default.
        app_context: The class of the app context, as for :class:`~arkitekt.App`.
    """

    @overload
    def __init__(
        self: "QtApp[None]",
        identifier: Optional[str] = None,
        version: str = "0.0.1",
        *,
        parent: Optional[Any] = None,
        logo: Optional[str] = None,
        scopes: Optional[List[str]] = None,
        author: Optional[str] = None,
        public_sources: Optional[List[PublicSource]] = None,
        services: Sequence[Service[Any]] = (),
        registry: Optional[AppRegistry] = None,
        app_context: None = None,
    ) -> None: ...

    @overload
    def __init__(
        self,
        identifier: Optional[str] = None,
        version: str = "0.0.1",
        *,
        parent: Optional[Any] = None,
        logo: Optional[str] = None,
        scopes: Optional[List[str]] = None,
        author: Optional[str] = None,
        public_sources: Optional[List[PublicSource]] = None,
        services: Sequence[Service[Any]] = (),
        registry: Optional[AppRegistry] = None,
        app_context: type[Ctx],
    ) -> None: ...

    def __init__(
        self,
        identifier: Optional[str] = None,
        version: str = "0.0.1",
        *,
        # A QtCore.QObject. qtpy re-exports the binding's classes at runtime, so
        # no checker can see the type; it is Any to them either way.
        parent: Optional[Any] = None,
        logo: Optional[str] = None,
        scopes: Optional[List[str]] = None,
        author: Optional[str] = None,
        public_sources: Optional[List[PublicSource]] = None,
        services: Sequence[Service[Any]] = (),
        registry: Optional[AppRegistry] = None,
        app_context: Optional[type[Ctx]] = None,
    ) -> None:
        super().__init__(  # type: ignore[misc]  # the overloads above are the contract
            identifier or _caller_module_name(),
            version,
            logo=logo,
            scopes=scopes,
            author=author,
            public_sources=public_sources,
            services=services,
            registry=registry,
            app_context=app_context,
        )
        self.parent = parent

    def _offer_with(
        self,
        actifier: Actifier,
        function: Callable[P, R],
        name: Optional[str],
        description: Optional[str],
        interface: Optional[str],
        widgets: Optional[Dict[str, AssignWidgetInput]],
        collections: Optional[List[str]],
        locks: Optional[List[str]],
    ) -> WrappedFunction[P, R]:
        decorate: Callable[[Callable[P, R]], WrappedFunction[P, R]] = self.action(
            actifier=actifier,
            name=name,
            description=description,
            interface=interface,
            widgets=widgets,
            collections=collections,
            locks=locks,
        )
        return decorate(function)

    def register_in_qt_loop(
        self,
        function: Callable[P, R],
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
        interface: Optional[str] = None,
        widgets: Optional[Dict[str, AssignWidgetInput]] = None,
        collections: Optional[List[str]] = None,
        locks: Optional[List[str]] = None,
    ) -> WrappedFunction[P, R]:
        """Offer a function that runs in the Qt event loop.

        For functions that may block the main thread on purpose, e.g. to prompt
        for input or show a modal dialog.

        Args:
            function: The function to offer.
            name: Display name. Defaults to the function name.
            description: Description. Defaults to the docstring.
            interface: Interface the action is offered at.
            widgets: Widgets per argument.
            collections: Collections the action is grouped into.
            locks: Locks held while an assignment runs.

        Returns:
            The function, registered.
        """
        from rekuest.qt.builders import qtinloopactifier

        return self._offer_with(
            qtinloopactifier, function, name, description, interface, widgets, collections, locks
        )

    def register_with_qt_future(
        self,
        function: Callable[P, R],
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
        interface: Optional[str] = None,
        widgets: Optional[Dict[str, AssignWidgetInput]] = None,
        collections: Optional[List[str]] = None,
        locks: Optional[List[str]] = None,
    ) -> WrappedFunction[P, R]:
        """Offer a function that answers through a future resolved in the Qt loop.

        The function's first parameter receives a ``QtFuture``; the assignment
        completes when a widget resolves it, e.g. from an "Accept" button::

            def ask(self, future: QtFuture[bool], question: str) -> None:
                self.dialog.show()
                self.pending = future       # on_accept: self.pending.resolve(True)

            app.register_with_qt_future(self.ask)

        Args:
            function: The function to offer.
            name: Display name. Defaults to the function name.
            description: Description. Defaults to the docstring.
            interface: Interface the action is offered at.
            widgets: Widgets per argument.
            collections: Collections the action is grouped into.
            locks: Locks held while an assignment runs.

        Returns:
            The function, registered.
        """
        from rekuest.qt.builders import qtwithfutureactifier

        return self._offer_with(
            qtwithfutureactifier, function, name, description, interface, widgets, collections, locks
        )

    def register_with_qt_generator(
        self,
        function: Callable[P, R],
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
        interface: Optional[str] = None,
        widgets: Optional[Dict[str, AssignWidgetInput]] = None,
        collections: Optional[List[str]] = None,
        locks: Optional[List[str]] = None,
    ) -> WrappedFunction[P, R]:
        """Offer a function that streams results through a generator driven from the Qt loop.

        The function's first parameter receives a ``QtGenerator``; each
        ``next(value)`` yields a result, and ``stop()`` ends the assignment.

        Args:
            function: The function to offer.
            name: Display name. Defaults to the function name.
            description: Description. Defaults to the docstring.
            interface: Interface the action is offered at.
            widgets: Widgets per argument.
            collections: Collections the action is grouped into.
            locks: Locks held while an assignment runs.

        Returns:
            The function, registered.
        """
        from rekuest.qt.builders import qtwithgeneratoractifier

        return self._offer_with(
            qtwithgeneratoractifier, function, name, description, interface, widgets, collections, locks
        )

    def wrap(self, function: Callable[P, R]) -> async_to_qt[R, P]:
        """Wrap a blocking function so Qt can run it off the main thread.

        Args:
            function: The blocking function.

        Returns:
            An ``async_to_qt`` task owned by :attr:`parent`: ``.run(...)`` starts it
            in a worker thread, and its signals report the result or error.
        """

        async def wrappable(*args: P.args, **kwargs: P.kwargs) -> R:
            return await run_threaded(function, *args, **kwargs)

        return async_to_qt(wrappable, parent=self.parent)
