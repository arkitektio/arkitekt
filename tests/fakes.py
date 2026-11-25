"""Fake clients and a fake provider for the app and runtime tests: no server.

The clients are ``@client`` classes a run builds through the offline fakts every
test gets (``conftest``). What they and the agent do is written to :data:`LOG`,
and each built client to :data:`BUILT`; both are emptied before every test.
"""

from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from typing import Annotated, Any, Self

from arkitekt_spec.declare.agents.connection import ConnectionListener, TaskListener
from arkitekt_spec.declare.app import AppRegistry
from arkitekt_spec.declare.provider import Provider
from fakts import Alias, Require
from rath.expansion import ExpandsStructures

from arkitekt import client, provider, structure
from arkitekt.app.app import App

LOG: list[str] = []
"""What the clients a run built and the fake agent did, in order."""

BUILT: list["FakeClient"] = []
"""Every client a run built, in build order."""


class FakeClient:
    """Records being entered and left."""

    def __init__(self, name: str, log: list[str] | None = None) -> None:
        self.name = name
        self.log = log if log is not None else []

    async def __aenter__(self) -> Self:
        self.log.append(f"enter {self.name}")
        return self

    async def __aexit__(self, *exc: Any) -> None:
        self.log.append(f"exit {self.name}")


class Picture:
    def __init__(self, id: str, owner: str) -> None:
        self.id = id
        self.owner = owner


@client(name="pictures")
class PictureClient(FakeClient, ExpandsStructures):
    """A client that expands its structures, as a generated client does.

    A run builds ``pictures-1``, ``pictures-2``, ... so two runs can be told apart.
    """

    async def aget_picture(self, id: str) -> Picture:
        return Picture(id, self.name)

    EXPANDERS = {"@pictures/picture": aget_picture}

    @classmethod
    def from_fakts(
        cls, pictures: Annotated[Alias, Require("live.test.pictures")]
    ) -> Self:
        count = sum(isinstance(c, PictureClient) for c in BUILT)
        built = cls(f"pictures-{count + 1}", LOG)
        BUILT.append(built)
        return built


@structure("@pictures/picture")
async def expand_picture(id: str, pictures: PictureClient) -> Picture:
    """A picture, by id."""
    return await pictures.aget_picture(id)


@client(name="other")
class OtherClient(FakeClient):
    """A second client, to test ordering and several clients."""

    @classmethod
    def from_fakts(cls, other: Annotated[Alias, Require("live.test.other")]) -> Self:
        built = cls("other", LOG)
        BUILT.append(built)
        return built


@client(name="rekuest")
class FakeRekuest(FakeClient, ExpandsStructures):
    """Stands in for the rekuest client. It knows nothing about any agent."""

    @classmethod
    def from_fakts(
        cls, rekuest: Annotated[Alias, Require("live.test.rekuest")]
    ) -> Self:
        built = cls("rekuest", LOG)
        BUILT.append(built)
        return built


class FakeAgent:
    """Stands in for the agent a run drives: records what it was handed and asked."""

    def __init__(self, client: FakeRekuest, log: list[str] | None = None) -> None:
        self.client = client
        self.log = log if log is not None else []
        self.provided: list[Any] = []
        self.bound_app: Any = None
        self.force: Any = None

    async def aprovide(self, context: object = None) -> None:
        self.provided.append(context)

    async def aconnect(
        self, context: object = None, timeout: float | None = None
    ) -> None:
        self.provided.append(context)

    async def aloop(self) -> None:
        return None

    async def __aenter__(self) -> "FakeAgent":
        self.log.append("enter agent")
        return self

    async def __aexit__(self, *exc: Any) -> None:
        self.log.append("exit agent")


def fake_provider() -> "Provider[FakeAgent]":
    """A provider building a :class:`FakeAgent` from the run's :class:`FakeRekuest`.

    An app that offers something is served by rekuest's provider unless it names
    one; this is the one to name, so a run never connects a real agent.
    """

    @provider(clients=[FakeRekuest])
    def rekuest_agent(registry: AppRegistry, client: FakeRekuest) -> FakeAgent:
        """The agent, from the client the run built."""
        return FakeAgent(client, LOG)

    return rekuest_agent


class RecordedRun:
    """Stands in for the runtime a CLI command connects: records what it is asked to run."""

    def __init__(
        self,
        app: App[Any],
        options: dict[str, object],
        runs: list[tuple[App[Any], dict[str, object]]],
        listener: ConnectionListener | None = None,
        fakts: object = None,
        during: "During | None" = None,
    ) -> None:
        self.app = app
        self.options = options
        self.runs = runs
        self.listener = listener
        self.fakts = fakts
        self.during = during
        self.task_listener: TaskListener | None = None

    async def arun(self, context: object = None) -> None:
        """Record the run as the user asked for it; then do what the test wants of it."""
        asked = (
            {**self.options, "context": context}
            if context is not None
            else self.options
        )
        self.runs.append((self.app, asked))
        if self.during is not None:
            await self.during(self)


During = Callable[[RecordedRun], Awaitable[None]]
"""What a test does inside a recorded run: raise, or drive its listener."""


def recording_connect(
    runs: list[tuple[App[Any], dict[str, object]]],
    fakts: object = None,
    during: During | None = None,
) -> Callable[..., AbstractAsyncContextManager[RecordedRun]]:
    """A stand-in for ``arkitekt.runtime.connect`` that connects nothing.

    ``runs`` collects ``(app, options)`` of every run, the options being what the
    user passed: what the CLI adds for itself (``provide``, the connection
    listener) is kept apart, on the yielded :class:`RecordedRun`. ``during`` is
    awaited with it inside the run, to raise or to drive the listener.
    """

    @asynccontextmanager
    async def fake_connect(
        app: App[Any],
        provide: bool = False,
        connection_listener: ConnectionListener | None = None,
        task_listener: TaskListener | None = None,
        **options: object,
    ) -> AsyncIterator[RecordedRun]:
        run = RecordedRun(
            app, options, runs, listener=connection_listener, fakts=fakts, during=during
        )
        run.task_listener = task_listener
        yield run

    return fake_connect


def write_session(
    identifier: str,
    version: str,
    url: str,
    logged_in_at: float | None = None,
    refreshed_at: float | None = None,
    deployment: str = "Lab",
    manifest_hash: str = "0" * 64,
    revocation_endpoint: str | None = None,
) -> str:
    """Save a session as a run would have, and return its path. Its tokens are
    recognisable, so a test can tell that none of them is ever shown."""
    import os
    import time

    from fakts.cache.file import CacheFile

    from arkitekt.app.sessions import session_path

    now = time.time()
    cached = CacheFile.model_validate(
        {
            "fakts": {
                "self": {
                    "deployment_name": deployment,
                    "alias": {
                        "id": "a",
                        "host": "h",
                        "port": 1,
                        "ssl": True,
                        "path": "p",
                        "challenge": "c",
                        "kind": "k",
                    },
                },
                "auth": {
                    "client_id": "client",
                    "token_endpoint": f"{url}/o/token/",
                    "revocation_endpoint": revocation_endpoint,
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
