"""Fake services and clients for the app and runtime tests: no fakts, no server."""

from contextlib import asynccontextmanager
from typing import Annotated, Any, AsyncIterator, Dict, List, Optional

from arkitekt_spec.declare.app import AppRegistry
from arkitekt_spec.declare.provider import Provider
from arkitekt_spec.declare.service import Service
from fakts import Alias, Require
from rath.expansion import ExpandsStructures


class FakeClient:
    """Records being entered and left."""

    def __init__(self, name: str, log: Optional[List[str]] = None) -> None:
        self.name = name
        self.log = log if log is not None else []

    async def __aenter__(self) -> "FakeClient":
        self.log.append(f"enter {self.name}")
        return self

    async def __aexit__(self, *exc: Any) -> None:
        self.log.append(f"exit {self.name}")


class Picture:
    def __init__(self, id: str, owner: str) -> None:
        self.id = id
        self.owner = owner


class PictureClient(FakeClient, ExpandsStructures):
    """A client that expands its service's structures, as a generated client does."""

    async def aget_picture(self, id: str) -> Picture:
        return Picture(id, self.name)

    EXPANDERS = {"@pictures/picture": aget_picture}


def PictureService(  # noqa: N802
    built: Optional[List[Any]] = None, log: Optional[List[str]] = None
) -> Service[PictureClient]:
    """A pictures service. Pass ``built`` to record the client of each build.

    Declared the way an SDK's ``arkitekt.py`` does: one registry, the service
    first, then the structure whose expander asks for the client it returns.
    A factory rather than a class: the caller's ``built`` and ``log`` lists are
    what the closure closes over. Clients are named ``pictures-1``,
    ``pictures-2``, ... in build order, so two runs can be told apart. Kept
    capitalised so it still reads as the thing an app is given.
    """
    record: List[Any] = built if built is not None else []
    registry = AppRegistry()

    @registry.service()
    def pictures(
        pictures: Annotated[Alias, Require("live.test.pictures")],
    ) -> PictureClient:
        """Pictures, for tests."""
        client = PictureClient(f"pictures-{len(record) + 1}", log)
        record.append(client)
        return client

    @registry.structure("@pictures/picture")
    async def expand_picture(id: str, pictures: PictureClient) -> Picture:
        """A picture, by id."""
        return await pictures.aget_picture(id)

    return pictures


class OtherClient(FakeClient):
    pass


def OtherService(  # noqa: N802
    log: Optional[List[str]] = None, client_cls: type = OtherClient
) -> Service[OtherClient]:
    """A second service, to test ordering and multiple clients.

    ``client_cls`` lets a test hand out a subclass (one that fails to enter, say).
    """

    @AppRegistry().service()
    def other(other: Annotated[Alias, Require("live.test.other")]) -> OtherClient:
        """Something else, for tests."""
        return client_cls("other", log)

    return other


class FakeRekuest(FakeClient, ExpandsStructures):
    """Stands in for the rekuest client. It knows nothing about any agent."""


class FakeAgent:
    """Stands in for the agent a run drives: records what it was handed and asked."""

    def __init__(self, client: FakeRekuest, log: Optional[List[str]] = None) -> None:
        self.client = client
        self.log = log if log is not None else []
        self.provided: List[Any] = []
        self.bound_app: Any = None
        self.force: Any = None

    async def aprovide(self, context: Any = None) -> None:  # noqa: ANN401
        self.provided.append(context)

    async def aconnect(self, context: Any = None, timeout: Any = None) -> None:  # noqa: ANN401
        self.provided.append(context)

    async def aloop(self) -> None:
        return None

    async def __aenter__(self) -> "FakeAgent":
        self.log.append("enter agent")
        return self

    async def __aexit__(self, *exc: Any) -> None:
        self.log.append("exit agent")


def RekuestProvider(log: Optional[List[str]] = None) -> "Provider[FakeAgent]":  # noqa: N802
    """The fake rekuest service and, beside it, the provider building a :class:`FakeAgent`.

    An app that offers something registers the real rekuest provider unless one
    is there already; this is the one to register first, so a run never tries
    to connect a real agent. Its service is named ``rekuest`` for the same reason.
    """
    registry = AppRegistry()

    @registry.service()
    def rekuest(rekuest: Annotated[Alias, Require("live.test.rekuest")]) -> FakeRekuest:
        """Rekuest, for tests."""
        return FakeRekuest("rekuest", log)

    @registry.provider()
    def rekuest_agent(registry: AppRegistry, client: FakeRekuest) -> FakeAgent:
        """The agent, from the client the run built."""
        return FakeAgent(client, log)

    return rekuest_agent


class RecordedRun:
    """Stands in for the runtime a CLI command connects: records what it is asked to run."""

    def __init__(
        self,
        app: Any,
        options: Dict[str, Any],
        runs: List[Any],
        listener: Any = None,
        fakts: Any = None,
        during: Any = None,
    ) -> None:
        self.app = app
        self.options = options
        self.runs = runs
        self.listener = listener
        self.fakts = fakts
        self.during = during

    async def arun(self, context: Any = None) -> None:  # noqa: ANN401
        """Record the run as the user asked for it; then do what the test wants of it."""
        asked = {**self.options, "context": context} if context is not None else self.options
        self.runs.append((self.app, asked))
        if self.during is not None:
            await self.during(self)


def recording_connect(runs: List[Any], fakts: Any = None, during: Any = None) -> Any:  # noqa: ANN401
    """A stand-in for ``arkitekt.runtime.connect`` that connects nothing.

    ``runs`` collects ``(app, options)`` of every run, the options being what the
    user passed: what the CLI adds for itself (``provide``, the connection
    listener) is kept apart, on the yielded :class:`RecordedRun`. ``during`` is
    awaited with it inside the run, to raise or to drive the listener.
    """

    @asynccontextmanager
    async def fake_connect(
        app: Any, provide: bool = False, connection_listener: Any = None, **options: Any  # noqa: ANN401
    ) -> AsyncIterator[RecordedRun]:
        yield RecordedRun(app, options, runs, listener=connection_listener, fakts=fakts, during=during)

    return fake_connect


def write_session(
    identifier: str,
    version: str,
    url: str,
    logged_in_at: Optional[float] = None,
    refreshed_at: Optional[float] = None,
    deployment: str = "Lab",
    manifest_hash: str = "0" * 64,
) -> str:
    """Save a session as a run would have, and return its path. Its tokens are
    recognisable, so a test can tell that none of them is ever shown."""
    import os
    import time

    from arkitekt.app.sessions import session_path
    from fakts.cache.file import CacheFile

    now = time.time()
    cached = CacheFile.model_validate(
        {
            "fakts": {
                "self": {
                    "deployment_name": deployment,
                    "alias": {"id": "a", "host": "h", "port": 1, "ssl": True, "path": "p", "challenge": "c", "kind": "k"},
                },
                "auth": {
                    "client_id": "client",
                    "token_endpoint": f"{url}/o/token/",
                    "refresh_token": "SECRET-REFRESH",
                    "access_token": "SECRET-ACCESS",
                    "chain_started_at": now if logged_in_at is None else logged_in_at,
                    "refresh_issued_at": now if refreshed_at is None else refreshed_at,
                },
                "instances": {},
                "statuses": {},
            },
            "created": "2026-10-01T10:00:00Z",
            "hash": manifest_hash + url,
        }
    )
    path = session_path(identifier, version, url)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as file:
        file.write(cached.model_dump_json())
    return path
