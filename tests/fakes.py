"""Fake services and clients for the app and runtime tests: no fakts, no server."""

from typing import Annotated, Any, List, Optional

from fakts import Alias, Require
from rath.expansion import ExpandsStructures
from rekuest.app import AppRegistry

from rekuest.provider import Provider
from rekuest.service import Service


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
