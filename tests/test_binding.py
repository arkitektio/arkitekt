"""A run builds each client with its binder, then the agent with its provider.

Requirements resolve through a testing fakts here, the way a run resolves them
through the deployment's.
"""

from typing import Annotated, Any, Self

import pytest
from arkitekt_spec.declare.app import AppRegistry
from arkitekt_spec.declare.client import client_of
from fakts import Alias, Require
from fakts.testing import build_testing_fakts

from arkitekt import client
from arkitekt.app.binding import ClientBuildError, build_client, build_provider


@client()
class Pictures:
    def __init__(self, url: str) -> None:
        self.url = url

    @classmethod
    def from_fakts(
        cls, pictures: Annotated[Alias, Require("live.test.pictures")]
    ) -> Self:
        return cls(pictures.to_http_path("graphql"))


@client(requires={})
class HandedOnly:
    """Has no binder: a run can only be handed one."""


@pytest.mark.asyncio
async def test_a_client_is_built_with_its_requirements_resolved() -> None:
    declaration = client_of(Pictures)
    assert declaration is not None
    async with build_testing_fakts(
        aliases={"pictures": "http://pictures-server"}
    ) as fakts:
        built = await build_client(declaration, fakts, AppRegistry())

    assert isinstance(built, Pictures)
    assert built.url.startswith("http://pictures-server")

    handed_only = client_of(HandedOnly)
    assert handed_only is not None
    with pytest.raises(ClientBuildError, match="hand one in"):
        await build_client(handed_only, None, AppRegistry())


@pytest.mark.asyncio
async def test_the_rekuest_provider_builds_its_agent_without_a_client() -> None:
    """The agent talks to rekuest over its own socket only; it takes no client."""
    from rekuest.agents.agent import RekuestAgent
    from rekuest.agents.transport.websocket import WebsocketAgentTransport
    from rekuest.arkitekt import rekuest_provider

    aliases: dict[str, Any] = {
        r.key: f"http://{r.key}-server" for r in rekuest_provider.get_requirements()
    }
    async with build_testing_fakts(aliases=aliases) as fakts:
        registry = AppRegistry()
        agent = await build_provider(rekuest_provider, fakts, registry, {})

    assert isinstance(agent, RekuestAgent)
    assert agent.app_registry is registry
    assert isinstance(agent.transport, WebsocketAgentTransport)
    assert agent.transport.endpoint_url.endswith("/agi")
