"""Static metadata for the deployment kinds -- importable without the ``server`` extra.

This module is deliberately **dependency-free**: plain dataclasses and strings, no
pydantic configs, no generators, no wizards. That matters because the CLI must be
able to describe the deployment groups (names, help text, which verbs they get) at
import time, while :mod:`arkitekt_next.server.deployments` -- which binds the real
config classes and generators -- transitively pulls in the optional ``server``
extra and may therefore only be imported inside a command callback.

:data:`KINDS` is the single source of truth for everything static;
``deployments.DEPLOYMENTS`` layers the heavy callables on top of it.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class KindMeta:
    """Static description of one deployment kind."""

    #: CLI group name, and the ``kind`` marker written into the profile YAML.
    name: str
    #: Profile YAML filename inside the deployment directory.
    filename: str
    #: Help text for the CLI group.
    help: str
    #: Whether the kind carries selectable data/compute services (``--service``).
    supports_services: bool = False
    #: Whether the kind deploys a gateway and web services, and can therefore be
    #: started on its own and health-checked. ``engine`` cannot: it is a lone
    #: deployer container that joins an *existing* deployment's external network,
    #: so it has no gateway to route ``/<service>/ht`` through.
    bootable: bool = True

    # --- config schema shape -------------------------------------------------
    # The four config classes are genuinely different schemas, not one schema with
    # optional fields, so anything that mutates a config generically has to know
    # which fields exist. These flags say so declaratively;
    # ``tests/cli/test_server_profiles.py`` asserts they match the real models.

    #: Config carries a ``deployer`` block (``ArkitektServerConfig``, ``EngineConfig``).
    has_deployer: bool = False
    #: Config carries ``db`` / ``minio`` infrastructure blocks.
    has_storage: bool = True
    #: Config carries a ``gateway`` block with exposed ports.
    has_gateway: bool = True


KINDS: dict[str, KindMeta] = {
    "hub": KindMeta(
        name="hub",
        filename="hub_config.yaml",
        supports_services=True,
        has_deployer=False,
        help="""Run a hub: a stack of Arkitekt services WITHOUT a local coordinator.

        A hub bundles the data/compute services (rekuest, mikro, fluss, ...) and
        trusts an external coordination (auth) server for identity. It manages no
        organizations or users, and comes with no deployer. Use `hub init` to write
        the config, `hub up` to compose and start the stack, and `hub connect` to
        register the hub's services with an organization. If you also want to run the
        coordinator locally, use `hubinator` instead.
        """,
    ),
    "coord": KindMeta(
        name="coord",
        filename="coord_config.yaml",
        has_deployer=False,
        help="""Run a coordinator: the standalone Lok auth server + Kontrol frontend.

        A coordinator issues identity (OIDC/JWKS via Lok) and serves the Kontrol web
        frontend that clients and hubs authenticate against. It runs no data/compute
        services and no deployer -- point one or more `hub`s at it via their
        `--coord-server`.
        """,
    ),
    "hubinator": KindMeta(
        name="hubinator",
        filename="hubinator_config.yaml",
        supports_services=True,
        has_deployer=True,
        help="""Run the full stack: a hub AND a local coordinator in one deployment.

        A hubinator is a self-contained Arkitekt instance -- the data/compute
        services plus a local Lok coordinator (with Kontrol frontend) and, optionally,
        a deployer. This is the all-in-one deployment the standalone arkitekt-server
        tool produced by default. Use `hubinator init` then `hubinator up`.
        """,
    ),
    "engine": KindMeta(
        name="engine",
        filename="engine_config.yaml",
        bootable=False,
        has_deployer=True,
        has_storage=False,
        has_gateway=False,
        help="""Run a standalone engine: a deployer in its own docker-compose.

        An engine is just a deployer running on its own. It connects to an existing
        Arkitekt deployment (a hub, coord or hubinator) and orchestrates app
        containers on its behalf. Only the `hubinator` bundles a deployer inline;
        everywhere else you run an engine. Use `engine init` then `engine up`.
        """,
    ),
}
