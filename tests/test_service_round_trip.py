"""Every installed service must actually build against a real fakts.

This is the check no single package's suite can make: a service module is
imported by its own tests, but nothing there *builds* it, so a builder that
constructs its client wrongly stays green everywhere.

It caught exactly that. Only rekuest's ``DataLayer`` models ``host``/``port``/
``protocol``; mikro's, elektro's, kraph's and dokuments' model ``endpoint_url``
alone, so a shared ``from_alias`` passing all four raised ``extra_forbidden`` on
four services out of five -- with every unit suite passing.

Services whose package is not installed, or which predate ``@service``, are
skipped, so this runs in arkitekt's own venv (where the client packages are the
published ones) as well as in a fully local checkout.
"""

import importlib
from typing import Any, Dict, List

import pytest
from arkitekt_spec.declare.app import AppRegistry
from arkitekt_spec.declare.service import Service
from fakts.testing import build_testing_fakts

#: Every package that declares a service, by the module and attribute it uses.
CANDIDATES = [
    "rekuest",
    "mikro",
    "elektro",
    "kraph",
    "fluss",
    "kabinet",
    "unlok",
    "alpaka",
    "lovekit",
    "dokuments",
]

#: A stand-in address per requirement key. Any key a service declares must be
#: here, or the test says so rather than skipping quietly.
ADDRESSES = {
    "rekuest": "http://rekuest-server",
    "mikro": "http://mikro-server",
    "elektro": "http://elektro-server",
    "kraph": "http://kraph-server",
    "fluss": "http://fluss-server",
    "kabinet": "http://kabinet-server",
    "alpaka": "http://alpaka-server",
    "lovekit": "http://lovekit-server",
    "dokuments": "http://dokuments-server",
    "livekit": "http://livekit-server",
    "s3": "http://store",
    "datalayer": "http://store",
}


def _declared_services() -> List[Service]:
    """The services of every candidate package that is installed and converted."""
    found: List[Service] = []
    for name in CANDIDATES:
        try:
            module = importlib.import_module(f"{name}.arkitekt")
        except Exception:  # noqa: BLE001 -- not installed, or broken for its own reasons
            continue
        declared = getattr(module, name, None)
        if isinstance(declared, Service):
            found.append(declared)
    return found


SERVICES = _declared_services()


def test_at_least_rekuest_is_here() -> None:
    """A guard on the guard: if nothing is collected, the rest asserts nothing."""
    assert any(s.name == "rekuest" for s in SERVICES), (
        "rekuest is a hard dependency of arkitekt, so its service must always be "
        f"collectable. Collected: {[s.name for s in SERVICES]}"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "declared", SERVICES, ids=lambda s: s.name
)
async def test_a_declared_service_builds_its_client(declared: Service) -> None:
    unknown = [r.key for r in declared.get_requirements() if r.key not in ADDRESSES]
    assert not unknown, (
        f"'{declared.name}' requires {unknown}, which this test has no "
        "address for. Add one to ADDRESSES."
    )

    aliases: Dict[str, Any] = {
        r.key: ADDRESSES[r.key] for r in declared.get_requirements()
    }
    async with build_testing_fakts(aliases=aliases) as fakts:
        client = await declared.build(fakts, AppRegistry())

    assert declared.returns is not None
    assert isinstance(client, declared.returns), (
        f"'{declared.name}' says it builds a "
        f"{declared.returns.__name__} but built a {type(client).__name__}"
    )


@pytest.mark.asyncio
async def test_the_rekuest_provider_builds_its_agent_without_a_client() -> None:
    """The agent talks to rekuest over its own socket only; it takes no client."""
    from fakts.testing import build_testing_fakts
    from rekuest.agents.backend import SocketAgentBackend
    from rekuest.agents.base import RekuestAgent
    from rekuest.arkitekt import rekuest_provider, rekuest_service

    aliases = {r.key: ADDRESSES[r.key] for r in rekuest_service.get_requirements()}
    async with build_testing_fakts(aliases=aliases) as fakts:
        registry = AppRegistry()
        agent = await rekuest_provider.build(fakts, registry, {})

    assert isinstance(agent, RekuestAgent)
    assert agent.app_registry is registry
    assert isinstance(agent.backend, SocketAgentBackend)
    assert agent.transport.endpoint_url.endswith("/agi")
