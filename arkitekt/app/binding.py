"""Build what an app declares: each client with its binder, then the agent with its provider.

A declaration says what a binder's parameters ask for; filling them is a run's. Each
requirement is resolved here, once, through the run's fakts: an alias is a route to
one service, and a live client is never moved to another.
"""

import inspect
from collections.abc import Mapping
from typing import Any

from arkitekt_spec.declare.app import AppRegistry
from arkitekt_spec.declare.client import ClientDeclaration
from arkitekt_spec.declare.injections import Injection
from arkitekt_spec.declare.provider import Provider
from fakts import Fakts

#: What a runtime's agent offers, checked by shape: the agent types are the runtime's.
_AGENT_LIFECYCLE = ("aprovide", "aconnect", "aloop", "force")


class ClientBuildError(LookupError):
    """A run could not build a client."""


class ProviderBuildError(LookupError):
    """A run could not build the provider's agent."""


async def _fill(
    owner: str,
    injections: list[Injection],
    fakts: Fakts | None,
    registry: AppRegistry,
    clients: Mapping[str, Any],
) -> dict[str, Any]:
    kwargs: dict[str, Any] = {}
    for injection in injections:
        if injection.kind == "registry":
            kwargs[injection.name] = registry
        elif injection.kind == "client":
            cls = injection.cls
            assert cls is not None, "a client injection carries its class"
            client = next((c for c in clients.values() if isinstance(c, cls)), None)
            if client is None:
                raise ProviderBuildError(
                    f"'{owner}' asks for a {cls.__name__} as '{injection.name}', but "
                    "this run has none: use that client in the app."
                )
            kwargs[injection.name] = client
        elif fakts is None:
            raise LookupError(
                f"'{owner}' needs the run's fakts for '{injection.name}', but this run "
                "built none."
            )
        elif injection.kind == "alias":
            require = injection.require
            assert require is not None, "an alias injection carries its Require"
            kwargs[injection.name] = await (
                fakts.aget_alias_or_none(injection.name)
                if require.optional
                else fakts.aget_alias(injection.name)
            )
        elif injection.kind == "own":
            kwargs[injection.name] = await fakts.aget_self_alias()
        elif injection.kind == "manifest":
            kwargs[injection.name] = fakts.manifest
        else:  # "tokens" and "fakts": the client is both
            kwargs[injection.name] = fakts
    return kwargs


async def build_client(
    client: ClientDeclaration[Any], fakts: Fakts | None, registry: AppRegistry
) -> object:
    """Build ``client`` with its binder, its requirements resolved through ``fakts``.

    Raises:
        ClientBuildError: If it has no binder (it can only be handed in), or the
            binder returns something else.
    """
    binder = client.binder_function
    if binder is None:
        raise ClientBuildError(
            f"{client.cls.__qualname__} has no binder: hand one in, "
            f"run(app, clients=[{client.cls.__qualname__}(...)])."
        )
    kwargs = await _fill(client.name, client.injections, fakts, registry, {})
    built = binder(**kwargs)
    built = await built if inspect.isawaitable(built) else built
    if not isinstance(built, client.cls):
        raise ClientBuildError(
            f"{client.cls.__qualname__}.{client.binder} returned a "
            f"{type(built).__name__}, not a {client.cls.__qualname__}."
        )
    return built


async def build_provider(
    provider: Provider[Any],
    fakts: Fakts | None,
    registry: AppRegistry,
    clients: Mapping[str, Any],
) -> Any:  # noqa: ANN401 -- the runtime's agent
    """Build the agent, not bound and not started: the run does both.

    Raises:
        ProviderBuildError: If it asks for a client the run has not got, or returns
            something that is not an agent.
    """
    try:
        kwargs = await _fill(
            provider.name, provider.injections, fakts, registry, clients
        )
    except LookupError as e:
        raise ProviderBuildError(str(e)) from e
    built = provider.function(**kwargs)
    agent = await built if inspect.isawaitable(built) else built
    if not all(hasattr(agent, name) for name in _AGENT_LIFECYCLE):
        raise ProviderBuildError(
            f"'{provider.name}' returned {type(agent).__name__}, which is not an "
            "agent: it must offer aprovide, aconnect, aloop and force."
        )
    return agent


__all__ = ["ClientBuildError", "ProviderBuildError", "build_client", "build_provider"]
