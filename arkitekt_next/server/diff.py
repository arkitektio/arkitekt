import difflib
import secrets
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict

from pydantic import BaseModel
import click
from .config import (
    ArkitektServerConfig,
    BaseService,
    DatenConfig,
    DeployerConfig,
    EmailConfig,
    GatewayConfig,
    KommunityPartner,
    LocalDBConfig,
    Membership,
    MinioConfig,
    Organization,
    RedisServiceConfig,
    RemoteDBConfig,
    GlobalAdminConfig,
    SpecificAdminConfig,
    LocalRedisConfig,
    LocalBucketConfig,
    RemoteRedisConfig,
    User,
    generate_alpha_numeric_string,
)
from .services import get_enabled_service_scopes
import yaml

if TYPE_CHECKING:
    from .config import CoordConfig, EngineConfig, HubConfig
    from .config.base import AdditionalAppConfig


# ---------------------------------------------------------------------------
# Generation context
#
# The building-block helpers below (``build_authentikate``,
# ``create_basic_config_values``, ``create_caddy_file`` ...) originally reached
# into a whole ``ArkitektServerConfig``. They now read a small, explicit
# ``GenContext`` instead, so the SAME helpers can be reused by the three
# dedicated per-path generators (``write_virtual_config_files`` for hubinator,
# ``write_hub_files`` for a hub, ``write_coord_files`` for a coordinator) even
# though those paths use different top-level schemas.
# ---------------------------------------------------------------------------


@dataclass
class GenContext:
    """Everything the shared generation helpers need, extracted from a profile."""

    # Infrastructure
    db: DatenConfig
    minio: MinioConfig
    local_redis: RedisServiceConfig
    gateway: GatewayConfig
    deployer: DeployerConfig
    internal_network: str
    device_id: str | None
    default_service_grace_period_seconds: int
    csrf_trusted_origins: list[str] | None

    # Identity / provisioning
    global_admin: str
    global_admin_password: str
    global_admin_email: str | None
    global_description: str | None
    organizations: list[Organization]
    users: list[User]
    memberships: list[Membership]
    email: EmailConfig | None
    kommunity_partners: list[KommunityPartner]
    apps: "dict[str, AdditionalAppConfig]"

    # Auth topology
    lok_enabled: bool
    lok: Any  # LokConfig | None -- Any avoids a circular services import
    coord_server: str
    rekuest_enabled: bool
    rekuest: Any  # RekuestConfig | None
    rekuest_server: str

    @classmethod
    def from_server_config(cls, config: ArkitektServerConfig) -> "GenContext":
        return cls(
            db=config.db,
            minio=config.minio,
            local_redis=config.local_redis,
            gateway=config.gateway,
            deployer=config.deployer,
            internal_network=config.internal_network,
            device_id=config.device_id,
            default_service_grace_period_seconds=config.default_service_grace_period_seconds,
            csrf_trusted_origins=config.csrf_trusted_origins,
            global_admin=config.global_admin,
            global_admin_password=config.global_admin_password,
            global_admin_email=config.global_admin_email,
            global_description=config.global_description,
            organizations=config.organizations,
            users=config.users,
            memberships=config.memberships,
            email=config.email,
            kommunity_partners=config.kommunity_partners,
            apps=config.apps,
            lok_enabled=config.lok.enabled,
            lok=config.lok,
            coord_server=config.coord_server,
            rekuest_enabled=config.rekuest.enabled,
            rekuest=config.rekuest,
            rekuest_server=config.rekuest_server,
        )

    @classmethod
    def from_hub_config(cls, config: "HubConfig") -> "GenContext":
        # A hub has no local coordinator (no Lok), manages no identities, and runs
        # no deployer (that is the `engine` command's job -- a disabled placeholder
        # keeps the context uniform).
        return cls(
            db=config.db,
            minio=config.minio,
            local_redis=config.local_redis,
            gateway=config.gateway,
            deployer=DeployerConfig(enabled=False),
            internal_network=config.internal_network,
            device_id=config.device_id,
            default_service_grace_period_seconds=config.default_service_grace_period_seconds,
            csrf_trusted_origins=config.csrf_trusted_origins,
            global_admin=config.global_admin,
            global_admin_password=config.global_admin_password,
            global_admin_email=config.global_admin_email,
            global_description=config.global_description,
            organizations=[],
            users=[],
            memberships=[],
            email=None,
            kommunity_partners=[],
            apps={},
            lok_enabled=False,
            lok=None,
            coord_server=config.coord_server,
            rekuest_enabled=config.rekuest.enabled,
            rekuest=config.rekuest,
            rekuest_server=config.rekuest_server,
        )

    @classmethod
    def from_coord_config(cls, config: "CoordConfig") -> "GenContext":
        # A coordinator IS the local coordination server (Lok) and runs no
        # data/compute services, so there is no local rekuest provenance authority
        # and no deployer (a disabled placeholder keeps the context uniform).
        return cls(
            db=config.db,
            minio=config.minio,
            local_redis=config.local_redis,
            gateway=config.gateway,
            deployer=DeployerConfig(enabled=False),
            internal_network=config.internal_network,
            device_id=config.device_id,
            default_service_grace_period_seconds=config.default_service_grace_period_seconds,
            csrf_trusted_origins=config.csrf_trusted_origins,
            global_admin=config.global_admin,
            global_admin_password=config.global_admin_password,
            global_admin_email=config.global_admin_email,
            global_description=config.global_description,
            organizations=config.organizations,
            users=config.users,
            memberships=config.memberships,
            email=config.email,
            kommunity_partners=config.kommunity_partners,
            apps={},
            lok_enabled=True,
            lok=config.lok,
            coord_server="local",
            rekuest_enabled=False,
            rekuest=None,
            rekuest_server="local",
        )


def iterate_services(all_services: list[BaseService]) -> list[BaseService]:
    """Filter a list of service configs down to the enabled ones.

    Note: ``lovekit`` is intentionally NOT part of the generated services -- it is
    a LiveKit/realtime service, not a Django web app, so callers do not pass it in.
    """
    services = []
    for service in all_services:
        if isinstance(service, BaseService):
            if service.enabled:
                services.append(service)
        else:
            raise TypeError(
                f"Expected BaseServiceConfig, got {type(service).__name__} instead."
            )

    return services


def iterate_service(config: ArkitektServerConfig) -> list[BaseService]:
    """Iterate over the enabled services in a full ``ArkitektServerConfig``.

    The explicit ordering here drives the order services are emitted into the
    generated compose file -- do not reorder. For a config-shape-agnostic version
    (hub/coord carry different fields), use :func:`iterate_any_service`.
    """
    return iterate_services(
        [
            config.rekuest,
            config.kabinet,
            config.mikro,
            config.fluss,
            config.elektro,
            config.lok,
            config.alpaka,
            config.kraph,
        ]
    )


#: Services in ``SERVICE_REGISTRY`` that are not Django web apps and therefore expose
#: no gateway-routed ``/<host>/ht`` endpoint. ``lovekit`` is a LiveKit/realtime
#: service; it is enabled by default but never deployed as a web service.
NON_WEB_SERVICES = frozenset({"lovekit"})


def iterate_any_service(config: BaseModel) -> list[BaseService]:
    """Enabled web services of *any* deployment config shape.

    Unlike :func:`iterate_service`, this does not assume the full
    ``ArkitektServerConfig`` schema. ``HubConfig`` carries no ``lok`` and
    ``CoordConfig`` carries no data services, so attribute access must be
    tolerant. Used for health checks and the CLI lifecycle commands, which run
    against all four deployment kinds.
    """
    from arkitekt_next.server.services import SERVICE_REGISTRY

    present = [
        service
        for name in SERVICE_REGISTRY
        if name not in NON_WEB_SERVICES
        and (service := getattr(config, name, None)) is not None
    ]
    return iterate_services(present)


def build_datalayer(ctx: GenContext, service: BaseService) -> Dict[str, Any]:
    """Build the ``datalayer`` (S3 storage) config block for a service.

    Emits the connection settings plus one ``{purpose: {bucket: <name>}}`` binding
    per bucket the service declares via ``get_buckets()``.
    """
    datalayer: dict[str, Any] = {
        "access_key": ctx.minio.access_key,
        "secret_key": ctx.minio.secret_key,
        "host": ctx.minio.host,
        "port": ctx.minio.internal_port,
        "protocol": "http",
        "region": "us-east-1",
    }
    for purpose, bucket in service.get_buckets().items():
        datalayer[purpose] = {"bucket": bucket.bucket_name}
    return datalayer


def build_authentikate(ctx: GenContext, service: BaseService) -> Dict[str, Any]:
    """Build the shared ``authentikate`` block (inbound token verification).

    Token verification points at the coordination server's JWKS:

    - When Lok runs locally (``coord_server == "local"``) the local Lok *is* the
      coordination server, so services fetch its JWKS over the internal network.
    - Otherwise services trust the remote coordination host's JWKS.

    Provenance (attestation) verification is nested under ``authentikate.provenance``
    and points at the rekuest server's JWKS:

    - When rekuest runs locally it is the provenance authority (internal JWKS).
    - Otherwise, if a remote rekuest host is configured, trust its JWKS.
    - With no provenance authority at all, the block is omitted entirely.

    The provenance block is only emitted for services that actually consume provenance
    tokens (``_verifies_provenance``); pure auth services like Lok/Lovekit reject it.
    """
    if ctx.lok_enabled:
        auth_issuer = {
            "kind": "jwks_uri",
            "iss": ctx.lok.issuer,
            # lok serves its JWKS from the OAuth2 endpoint (``/o/jwks/``), not from
            # ``/.well-known/jwks.json`` (cf. its openid-configuration). Services on
            # the internal network reach it under lok's ``/<host>`` path prefix.
            "jwks_uri": f"http://{ctx.lok.host}:{ctx.lok.internal_port}"
            f"/{ctx.lok.host}/o/jwks/",
        }
    else:
        auth_issuer = {
            "kind": "jwks_uri",
            "iss": ctx.coord_server,
            "jwks_uri": f"https://{ctx.coord_server}/.well-known/jwks.json",
        }

    authentikate: dict[str, Any] = {
        "issuers": [auth_issuer],
        "static_tokens": {},
    }

    prov_issuer: dict[str, Any] | None = None
    if not getattr(service, "_verifies_provenance", True):
        return authentikate
    if ctx.rekuest_enabled:
        prov_issuer = {
            "kind": "jwks_uri",
            "iss": ctx.rekuest.provenance_issuer,
            "jwks_uri": f"http://{ctx.rekuest.host}:{ctx.rekuest.internal_port}"
            f"/{ctx.rekuest.host}/.well-known/jwks.json",
        }
    elif ctx.rekuest_server and ctx.rekuest_server not in ("local", "none", ""):
        prov_issuer = {
            "kind": "jwks_uri",
            "iss": ctx.rekuest_server,
            "jwks_uri": f"https://{ctx.rekuest_server}/.well-known/jwks.json",
        }

    if prov_issuer is not None:
        authentikate["provenance"] = {"issuers": [prov_issuer]}

    return authentikate


def create_basic_config_values(
    ctx: GenContext, service: BaseService
) -> Dict[str, Any]:
    """
    Create the common configuration blocks shared by every Arkitekt service.

    Produces the new-schema layout documented under ``docs/config`` -- the
    ``django``, ``postgres``, ``redis`` and ``authentikate`` blocks, plus an
    optional ``datalayer`` block for services that use S3 storage and a
    ``provenance`` block for services that sign provenance attestations.

    Args:
        config: The main Arkitekt server configuration
        service: The specific service configuration to generate values for

    Returns:
        A dictionary containing the service configuration values

    Raises:
        TypeError: If the service has an unsupported database or Redis configuration type
    """
    if isinstance(service.db_config, LocalDBConfig):
        postgres = {
            "engine": "django.db.backends.postgresql",
            "db_name": service.db_config.db,
            "username": ctx.db.postgres_user,
            "password": ctx.db.postgres_password,
            "host": "db",
            "port": 5432,
        }
    elif isinstance(service.db_config, RemoteDBConfig):
        postgres = {
            "engine": "django.db.backends.postgresql",
            "db_name": service.db_config.db,
            "username": service.db_config.user,
            "password": service.db_config.password,
            "host": service.db_config.host,
            "port": service.db_config.port,
        }
    else:
        raise TypeError(
            f"Expected LocalDBConfig or RemoteDBConfig, got {type(service.db_config).__name__} instead."
        )

    if isinstance(service.admin_config, GlobalAdminConfig):
        django_admin = {
            "username": ctx.global_admin,
            "password": ctx.global_admin_password,
            "email": ctx.global_admin_email,
        }
    elif isinstance(service.admin_config, SpecificAdminConfig):
        django_admin = {
            "username": service.admin_config.username,
            "password": service.admin_config.password,
            "email": service.admin_config.email,
        }
    else:
        raise TypeError(
            f"Expected GlobalAdminConfig or SpecificAdminConfig, got {type(service.admin_config).__name__} instead."
        )

    if isinstance(service.redis_config, LocalRedisConfig):
        redis = {
            "host": ctx.local_redis.host,
            "port": ctx.local_redis.internal_port,
        }
    elif isinstance(service.redis_config, RemoteRedisConfig):
        redis = {
            "host": service.redis_config.host,
            "port": service.redis_config.port,
        }
    else:
        raise TypeError(
            f"Expected LocalRedisConfig or RemoteRedisConfig, got {type(service.redis_config).__name__} instead."
        )

    config_values: dict[str, Any] = {
        "django": {
            "secret_key": service.secret_key,
            "debug": service.debug,
            "hosts": service.allowed_hosts,
            "admin": django_admin,
            "csrf_trusted_origins": ctx.csrf_trusted_origins
            or ["http://localhost", "https://localhost"],
            # Path prefix this service is served under behind the gateway. Emitted
            # WITHOUT a leading slash: services use it only to build external URLs
            # (``MY_SCRIPT_NAME``) as ``build_absolute_uri("/") + MY_SCRIPT_NAME``,
            # so a leading slash would yield a double slash (e.g. ``//lok/o/token/``)
            # and break the rendered OAuth/token endpoints.
            "force_script_name": f"{service.host}",
        },
        "postgres": postgres,
        "redis": redis,
        "authentikate": build_authentikate(ctx, service),
    }

    if getattr(service, "_uses_datalayer", False):
        config_values["datalayer"] = build_datalayer(ctx, service)

    # Rekuest (and any service with a provenance keypair) signs attestations.
    if hasattr(service, "provenance_key_pair"):
        config_values["provenance"] = {
            "issuer": service.provenance_issuer,
            "kid": service.provenance_kid,
            "private_key": service.provenance_key_pair.private_key,
            "public_key": service.provenance_key_pair.public_key,
        }

    return config_values


def clone_repo(github_repo: str, target_dir: str, base_dir: Path):
    """Clone a GitHub repository into a target directory."""

    if (Path(base_dir) / Path(target_dir)).exists():
        # Check if the directory is the github repo of this service
        if (Path(base_dir) / Path(target_dir) / ".git").exists():
            # check if origin is remote
            result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                check=True,
                capture_output=True,
                cwd=Path(base_dir) / Path(target_dir),
            )
            if result.returncode == 0:
                if result.stdout:
                    if not result.stdout.strip().decode("utf-8") == github_repo:
                        raise ValueError(
                            f"Already cloned repository at path {Path(base_dir) / Path(target_dir)} of already present repository does not match expected {github_repo}. Got: {result.stdout.strip()}. Please remove directory manually before proceeding"
                        )
                    else:
                        print(
                            f"Directory {target_dir} is already a git repository with matching remote origin, skipping clone...."
                        )
                else:
                    raise ValueError(
                        f"Directory {target_dir} is already a git repository without remote origin. Please check this before proceeding."
                    )

            else:
                raise ValueError(
                    f"Directory {target_dir} is a git repository without remote origin. Please check this before proceeding."
                )
    else:
        subprocess.run(
            ["git", "clone", github_repo, target_dir], check=True, cwd=base_dir
        )


def create_config(
    service_name: str, config_values: Dict[str, Any], base_path: Path
) -> None:
    """Create a service configuration dictionary."""
    service_dir = base_path / "configs"
    service_dir.mkdir(parents=True, exist_ok=True)

    (service_dir / f"{service_name}.yaml").write_text(
        yaml.dump(config_values, default_flow_style=False)
    )


def build_default_service(path: Path, service: BaseService) -> dict[str, Any]:
    """
    Build a default Docker Compose service definition.

    Creates a standard service configuration for Docker Compose with common
    settings like image, command, dependencies, and volume mounts.

    Args:
        path: Deployment directory (used when cloning a service repo for dev builds)
        service: The service to create a Docker Compose definition for

    Returns:
        A dictionary representing a Docker Compose service definition
    """

    docker_service = {
        "image": service.image,
        "command": service.build_run_command(),
        "depends_on": ["redis", "db", "minio"],
        "stop_grace_period": "2s",
        "volumes": [f"./configs/{service.host}.yaml:/workspace/config.yaml"],
        "deploy": {
            "restart_policy": {
                "condition": "on-failure",
                "delay": "10s",
                "max_attempts": 10,
                "window": "300s",
            }
        },
    }

    if service.mount_github:
        cloned_repo = f"./repos/{service.host}"
        clone_repo(
            github_repo=service.github_repo, target_dir=cloned_repo, base_dir=path
        )

        docker_service["volumes"].append(
            f"./repos/{service.host}:/workspace/repos/{service.host}"
        )

        del docker_service["image"]
        docker_service["build"] = cloned_repo

    return docker_service


def parse_local_db_requests(services: list[BaseService]) -> list[LocalDBConfig]:
    """Collect the local-database requests from an already-enabled service list.

    Used to determine which databases must be created in the PostgreSQL container.
    """
    db_names: list[LocalDBConfig] = []
    for service in services:
        if isinstance(service.db_config, LocalDBConfig):
            db_names.append(service.db_config)
    return db_names


def parse_local_redis_request(services: list[BaseService]) -> list[LocalRedisConfig]:
    """Collect the local-Redis requests from an already-enabled service list.

    Used to determine whether a Redis container needs to be started.
    """
    redis_dbs: list[LocalRedisConfig] = []
    for service in services:
        if isinstance(service.redis_config, LocalRedisConfig):
            redis_dbs.append(service.redis_config)
    return redis_dbs


def parse_local_bucket_configs(
    services: list[BaseService],
) -> list[LocalBucketConfig]:
    """Collect the local MinIO bucket requests from an already-enabled service list.

    Used to determine which S3 buckets must be created in the MinIO container.
    """
    bucket_names: list[LocalBucketConfig] = []
    for service in services:
        buckets = service.get_buckets()
        if isinstance(buckets, dict):
            for bucket_name, bucket_config in buckets.items():
                if isinstance(bucket_config, LocalBucketConfig):
                    bucket_names.append(bucket_config)
    return bucket_names


def create_caddyfilepath(service: BaseService) -> str:
    """
    Create a Caddyfile path matcher and handler for a single service.

    This is a helper function that generates the Caddy configuration block
    for routing requests to a specific service based on URL path matching.

    Args:
        service: The service to create routing configuration for

    Returns:
        A string containing the Caddy configuration block for this service
    """
    caddyfile = f"\t@{service.host} path /{service.host}*\n"
    caddyfile += "\thandle @" + service.host + " { \n"
    caddyfile += f"\t\treverse_proxy {service.host}:{service.internal_port}\n"
    caddyfile += "\t}\n\n"
    return caddyfile


def create_caddy_file(ctx: GenContext, services: list[BaseService]) -> str:
    """
    Create a Caddyfile for reverse proxy configuration.

    Generates a Caddy reverse proxy configuration that routes requests to the
    appropriate services based on URL paths. This includes:
    - Service routing (e.g., /rekuest/* -> rekuest service)
    - Bucket routing for MinIO access
    - Special routes like /.well-known for OAuth/OIDC
    - MinIO admin interface routing

    Args:
        ctx: The generation context (MinIO + auth topology)
        services: The enabled services to route to

    Returns:
        A string containing the complete Caddyfile configuration

    Raises:
        TypeError: If a service doesn't implement the BaseService protocol
    """

    caddyfile = "http:// {\n"

    for service in services:
        if not isinstance(service, BaseService):
            raise TypeError(
                f"Expected BaseServiceConfig, got {type(service).__name__} instead."
            )
        caddyfile += f"\t@{service.host} path /{service.host}*\n"
        caddyfile += "\thandle @" + service.host + " { \n"
        caddyfile += f"\t\treverse_proxy {service.host}:{service.internal_port}\n"
        caddyfile += "\t}\n\n"

    for bucket in parse_local_bucket_configs(services):
        caddyfile += f"\t@{bucket.bucket_name} path /{bucket.bucket_name}*\n"
        caddyfile += "\thandle @" + bucket.bucket_name + " { \n"
        caddyfile += (
            f"\t\treverse_proxy {ctx.minio.host}:{ctx.minio.internal_port}\n"
        )
        caddyfile += "\t}\n\n"

    # Serve the coordination JWKS / OIDC discovery at the root well-known path only
    # when Lok runs locally as the coordination server. With a remote coordination
    # server, clients resolve /.well-known against that server directly.
    if ctx.lok_enabled:
        caddyfile += "\t@.well-known path /.well-known/*\n"
        caddyfile += "\thandle @.well-known {\n"
        caddyfile += "\t\trewrite * /lok{uri}\n"
        caddyfile += f"\t\treverse_proxy {ctx.lok.host}:{ctx.lok.internal_port}\n"
        caddyfile += "\t}\n\n"

    caddyfile += "\t@minio path /minio/*\n"
    caddyfile += "\thandle @minio {\n"
    caddyfile += f"\t\treverse_proxy {ctx.minio.host}:{ctx.minio.internal_port}\n"
    caddyfile += "\t}\n\n"

    caddyfile += "}\n"
    return caddyfile


class AliasConfig(BaseModel):
    """
    Configuration for service aliases in the Arkitekt ecosystem.

    Aliases define how services are exposed and accessed through different
    protocols and layers (e.g., HTTP, WebSocket, public/private access).

    Attributes:
        challenge: The challenge type for authentication/access
        kind: The protocol or connection type (e.g., 'http', 'ws')
        layer: The access layer (e.g., 'public', 'private')
        path: The URL path where the service is accessible
    """

    challenge: str
    kind: str
    layer: str
    path: str | None = None


class InstanceConfig(BaseModel):
    """
    Configuration for a service instance in the Arkitekt ecosystem.

    Instances represent deployed services that can be discovered and
    connected to by other services or client applications.

    Attributes:
        service: The service type identifier (e.g., 'live.arkitekt.rekuest')
        identifier: Unique identifier for this instance
        alias: List of aliases defining how to access this instance
    """

    service: str
    identifier: str
    aliases: list[AliasConfig] = []


class RedeemTokenConfig(BaseModel):
    """
    Configuration for redeem tokens used in service authentication.

    Redeem tokens allow services or users to exchange temporary tokens
    for persistent authentication credentials.

    Attributes:
        token: The redeemable token string
        user: The user associated with this token
    """

    token: str
    user: str
    organization: str
    hub: str = "localhost"


# Identifier of the auto-configured hub that bundles every local service.
LOCAL_HUB_IDENTIFIER = "localhost"


def build_local_kommunity_partner(
    ctx: GenContext, services: list[BaseService]
) -> dict[str, Any]:
    """Build a lok ``kommunity_partner`` that auto-configures a local hub.

    The hub (identifier ``localhost``) registers every enabled service as an
    instance so that clients authenticating against this deployment receive working
    aliases for them. The emitted shape matches lok's ``KommunityPartnerModel`` /
    ``HubManifest`` schema (see ``docs/config/lok.md``).
    """
    instances: list[dict[str, Any]] = []
    for service in services:
        identifier = service.get_identifier()
        instances.append(
            {
                "identifier": f"local_{service.host}",
                "manifest": {
                    "identifier": f"live.arkitekt.{identifier}",
                    "version": "1.0.0",
                    "description": service.get_description(),
                    "roles": [r.model_dump() for r in service.get_roles()],
                    "scopes": [s.model_dump() for s in service.get_scopes()],
                },
                "aliases": [
                    {
                        "id": f"local_{service.host}",
                        "name": service.get_name(),
                        # Relative alias: lok resolves host/port/ssl from the gateway
                        # request and serves it under this path (``/<service>``). Do
                        # NOT set ``port`` -- doing so overrides the gateway's port.
                        "host": service.host,
                        "path": service.host,
                        "challenge": "ht",
                        "kind": "relative",
                        "scope": "public",
                        "ssl": False,
                    }
                ],
            }
        )

    # MinIO is not a Django web service, so ``iterate_service`` does not yield it,
    # yet storage clients (e.g. mikro) declare a ``live.arkitekt.s3`` requirement.
    # Register the object store as a hub instance so those clients can be
    # composed -- the gateway routes ``/minio/*`` to MinIO, and the client reads
    # only the endpoint URL from this alias (upload credentials are minted by the
    # owning service).
    if ctx.minio.enabled:
        instances.append(
            {
                "identifier": f"local_{ctx.minio.host}",
                "manifest": {
                    "identifier": "live.arkitekt.s3",
                    "version": "1.0.0",
                    "description": "Local S3 / MinIO object storage datalayer",
                    "roles": [],
                    "scopes": [],
                },
                "aliases": [
                    {
                        "id": f"local_{ctx.minio.host}",
                        "name": "S3",
                        # Relative alias with NO path: the endpoint resolves to the
                        # gateway root, so S3 path-style requests (``/<bucket>/...``)
                        # hit the per-bucket gateway routes. The challenge targets
                        # MinIO's health endpoint, which the gateway serves (unstripped)
                        # under ``/minio/health/live``.
                        "host": ctx.minio.host,
                        "challenge": "minio/health/live",
                        "kind": "relative",
                        "scope": "public",
                        "ssl": False,
                    }
                ],
            }
        )

    return {
        "identifier": "local_arkitekt",
        "name": "Local Arkitekt Services",
        "website_url": "localhost",
        "partner_kind": "preauthorized",
        "auto_configure": True,
        "preconfigured_hub": {
            "identifier": LOCAL_HUB_IDENTIFIER,
            "instances": instances,
        },
    }


def service_to_instance_config(
    service: BaseService, service_name: str
) -> InstanceConfig:
    """
    Convert a service configuration to an instance configuration.

    This creates the instance metadata that gets registered with the Lok
    authentication service, allowing other services and clients to discover
    and connect to this service instance.

    Args:
        service: The service configuration to convert
        service_name: The canonical service name (e.g., 'live.arkitekt.rekuest')

    Returns:
        An InstanceConfig object representing this service instance
    """
    return InstanceConfig(
        service=service_name,
        identifier=service.host,
        aliases=[
            AliasConfig(
                challenge="ht", kind="relative", layer="public", path=service.host
            )
        ],
    )


# ---------------------------------------------------------------------------
# Emit helpers
#
# Each ``_emit_*`` helper appends compose service definitions to the ``out`` dict
# and writes any mounted config files. They are the shared building blocks reused
# by the three dedicated per-path generators below. They read only a lightweight
# ``GenContext`` plus explicit service lists, so they work regardless of which
# top-level profile schema drives them.
# ---------------------------------------------------------------------------


def _provision_org_bots(ctx: GenContext) -> None:
    """Append a bot user + bot membership for each organization (in place)."""
    for org in ctx.organizations:
        bot_username = org.bot_name
        ctx.users.append(
            User(
                username=bot_username,
                password=generate_alpha_numeric_string(12),
                email=None,
            )
        )
        ctx.memberships.append(
            Membership(
                user=bot_username,
                organization=org.identifier,
                roles=["bot"],
            )
        )


def _emit_infrastructure(
    ctx: GenContext,
    services: list[BaseService],
    tmpdir: Path,
    out: Dict[str, Any],
) -> None:
    """Emit Postgres / Redis / MinIO containers required by ``services``."""
    # Configure PostgreSQL database if any services need local databases
    local_dbs = parse_local_db_requests(services)
    if len(local_dbs) >= 1:
        out["db"] = {
            "image": ctx.db.image,
            "environment": {
                "POSTGRES_MULTIPLE_DATABASES": ",".join(
                    [request.db for request in local_dbs]
                ),
                "POSTGRES_PASSWORD": ctx.db.postgres_password,
                "POSTGRES_USER": ctx.db.postgres_user,
            },
            "volumes": [
                f"{ctx.db.mount or ctx.db.volume_name}:/var/lib/postgresql/data"
            ],
        }

    # Configure Redis service if any services need local Redis
    local_redis_requests = parse_local_redis_request(services)
    if len(local_redis_requests) >= 1:
        out[ctx.local_redis.host] = {
            "image": ctx.local_redis.image,
        }

    # Configure MinIO object storage if any services need local buckets
    local_bucket_requests = parse_local_bucket_configs(services)
    if len(local_bucket_requests) >= 1:
        out[ctx.minio.host] = {
            "image": ctx.minio.image,
            "command": "server /data",
            "environment": {
                "MINIO_ROOT_USER": ctx.minio.root_user,
                "MINIO_ROOT_PASSWORD": ctx.minio.root_password,
            },
            "stop_grace_period": "2s",
            "volumes": [f"{ctx.minio.mount or ctx.minio.volume_name}:/data"],
        }

        # Configuration for MinIO initialization (creates buckets and users)
        init_config: dict[str, Any] = {
            "buckets": [{"name": req.bucket_name} for req in local_bucket_requests],
            "users": [
                {
                    "access_key": ctx.minio.access_key,
                    "secret_key": ctx.minio.secret_key,
                    "policies": ["readwrite"],
                    "name": "Default User",
                }
            ],
        }

        create_config(ctx.minio.init_container_host, init_config, tmpdir)
        # MinIO initialization container that sets up buckets and users on startup
        out[ctx.minio.init_container_host] = {
            "image": ctx.minio.init_container_image,
            "volumes": [
                f"./configs/{ctx.minio.init_container_host}.yaml:/workspace/config.yaml"
            ],
            "stop_grace_period": "2s",
            "environment": {
                "MINIO_ROOT_USER": ctx.minio.root_user,
                "MINIO_ROOT_PASSWORD": ctx.minio.root_password,
                "MINIO_HOST": f"http://{ctx.minio.host}:{ctx.minio.internal_port}",
            },
            "depends_on": {ctx.minio.host: {"condition": "service_started"}},
        }


def _emit_deployer(
    ctx: GenContext, out: Dict[str, Any], redeem_tokens: list[RedeemTokenConfig]
) -> None:
    """Emit one deployer container per organization for app orchestration."""
    if not ctx.deployer.enabled:
        return
    for org in ctx.organizations:
        token = secrets.token_hex(16)

        out[ctx.deployer.host + org.name] = {
            "image": ctx.deployer.image,
            "volumes": ["/var/run/docker.sock:/var/run/docker.sock"],
            "command": (
                f"arkitekt-next app run prod --redeem-token={token} "
                f"--url http://{ctx.gateway.host}:{ctx.gateway.internal_port}"
            ),
            "stop_grace_period": "2s",
            "deploy": {
                "restart_policy": {
                    "condition": "on-failure",
                    "delay": "10s",
                    "max_attempts": 10,
                    "window": "300s",
                }
            },
            "environment": {
                "ARKITEKT_GATEWAY": f"http://{ctx.gateway.host}:{ctx.gateway.internal_port}",
                "ARKITEKT_NETWORK": ctx.internal_network,
                "INSTANCE_ID": "default",
                "ME_ID": f"{org.identifier}_default",
                "DEPLOYER_ORGANIZATION": org.identifier,
            },
        }

        redeem_tokens.append(
            RedeemTokenConfig(
                token=token, user=org.bot_name, organization=org.identifier
            )
        )


def _emit_apps(
    ctx: GenContext, out: Dict[str, Any], redeem_tokens: list[RedeemTokenConfig]
) -> None:
    """Emit one container per additional-app instance per organization."""
    if not ctx.apps:
        return
    for org in ctx.organizations:
        for key, app in ctx.apps.items():
            for instance in app.instances:
                token = secrets.token_hex(16)

                out[key + "_" + instance + "_" + org.identifier] = {
                    "image": app.image,
                    "command": (
                        f"arkitekt-next app run prod --redeem-token={token} "
                        f"--url http://{ctx.gateway.host}:{ctx.gateway.internal_port}"
                    ),
                    "stop_grace_period": f"{app.grace_period_seconds or ctx.default_service_grace_period_seconds}s",
                    "deploy": {
                        "restart_policy": {
                            "condition": "on-failure",
                            "delay": "10s",
                            "max_attempts": 10,
                            "window": "300s",
                        }
                    },
                    "environment": {
                        "ARKITEKT_GATEWAY": f"http://{ctx.gateway.host}:{ctx.gateway.internal_port}",
                        "ARKITEKT_NETWORK": ctx.internal_network,
                        "ARKITEKT_DEVICE_ID": ctx.device_id,
                        "INSTANCE_ID": instance,
                    },
                }

                user = app.user or org.bot_name
                organization = app.organization or org.identifier

                redeem_tokens.append(
                    RedeemTokenConfig(
                        token=token,
                        user=user,
                        organization=organization,
                    )
                )


def _emit_data_services(
    ctx: GenContext,
    data_services: list[BaseService],
    tmpdir: Path,
    out: Dict[str, Any],
) -> None:
    """Emit each data/compute service container plus its mounted config file."""
    for service in data_services:
        out[service.host] = build_default_service(tmpdir, service)
        create_config(
            service.host, create_basic_config_values(ctx, service), tmpdir
        )


def _emit_gateway(
    ctx: GenContext,
    routed_services: list[BaseService],
    tmpdir: Path,
    out: Dict[str, Any],
) -> None:
    """Emit the Caddy gateway container and write its Caddyfile."""
    exposed_ports = []
    if ctx.gateway.exposed_http_port:
        exposed_ports.append(f"{ctx.gateway.exposed_http_port}:80")
    if ctx.gateway.exposed_https_port:
        exposed_ports.append(f"{ctx.gateway.exposed_https_port}:443")

    out[ctx.gateway.host] = {
        "image": ctx.gateway.image,
        "ports": exposed_ports,
        "networks": [ctx.internal_network, "default"],
        "volumes": ["./configs/Caddyfile:/etc/caddy/Caddyfile"],
    }

    caddyfile = create_caddy_file(ctx, routed_services)
    configs_dir = tmpdir / "configs"
    configs_dir.mkdir(parents=True, exist_ok=True)
    (configs_dir / "Caddyfile").write_text(caddyfile)


def _emit_lok(
    ctx: GenContext,
    routed_services: list[BaseService],
    tmpdir: Path,
    out: Dict[str, Any],
    redeem_tokens: list[RedeemTokenConfig],
) -> None:
    """Emit the Lok coordinator container and its ``configs/lok.yaml`` provisioning."""
    default_lok_service = build_default_service(tmpdir, ctx.lok)
    default_lok_service["environment"] = {
        "AUTHLIB_INSECURE_TRANSPORT": "true",
    }
    out[ctx.lok.host] = default_lok_service

    lok_config = create_basic_config_values(ctx, ctx.lok)

    # Lok's own published key material (verifies the tokens it issues).
    lok_config["lok"] = {
        "public_key": ctx.lok.auth_key_pair.public_key,
        "static_tokens": {},
    }

    # Top-level OIDC / provisioning fields (live at the root of the lok config).
    lok_config["private_key"] = ctx.lok.auth_key_pair.private_key
    lok_config["oidc_issuer"] = f"http://{ctx.lok.host}"

    lok_config["deployment"] = {
        "name": ctx.internal_network,
        "description": ctx.global_description or "A Basic Arkitekt Deployment",
    }

    if ctx.email:
        lok_config["email"] = {
            "host": ctx.email.host,
            "port": ctx.email.port,
            "user": ctx.email.username,
            "password": ctx.email.password,
            "email": ctx.email.email,
        }

    # Provisioning data applied on boot. lok requires every organization to have a
    # (string) owner, so default it to the global admin, and make sure that admin
    # exists as a superuser so the owner/creator references resolve.
    org_dumps: list[dict[str, Any]] = []
    for org in ctx.organizations:
        org_dump = org.model_dump()
        if not org_dump.get("owner"):
            org_dump["owner"] = ctx.global_admin
        org_dumps.append(org_dump)
    lok_config["organizations"] = org_dumps

    user_dumps: list[dict[str, Any]] = [user.model_dump() for user in ctx.users]
    user_dumps.append(
        {
            "username": ctx.global_admin,
            "password": ctx.global_admin_password,
            "email": ctx.global_admin_email,
            "is_superuser": True,
            "is_staff": True,
        }
    )
    lok_config["users"] = user_dumps
    lok_config["memberships"] = [
        membership.model_dump() for membership in ctx.memberships
    ]
    lok_config["redeem_tokens"] = [token.model_dump() for token in redeem_tokens]
    # Auto-configure a local hub bundling every enabled service, plus any
    # explicitly configured partners.
    lok_config["kommunity_partners"] = [
        build_local_kommunity_partner(ctx, routed_services)
    ] + [partner.model_dump() for partner in ctx.kommunity_partners]

    create_config(ctx.lok.host, lok_config, tmpdir)


def _finalize_compose(
    ctx: GenContext, out: Dict[str, Any], tmpdir: Path
) -> None:
    """Assemble and write ``docker-compose.yaml`` from the emitted services."""
    volumes: list[str] = []
    if not ctx.db.mount:
        volumes.append(f"{ctx.db.volume_name}")
    if not ctx.minio.mount:
        volumes.append(f"{ctx.minio.volume_name}")

    docker_compose_content: Dict[str, Any] = {
        "services": out,
        "networks": {
            ctx.internal_network: {
                "driver": "bridge",
                "name": ctx.internal_network,
            }
        },
        "volumes": {vol: {} for vol in volumes},
    }

    (tmpdir / "docker-compose.yaml").write_text(
        yaml.dump(docker_compose_content, default_flow_style=False)
    )


# ---------------------------------------------------------------------------
# Dedicated per-path generators
# ---------------------------------------------------------------------------


def write_virtual_config_files(tmpdir: Path, config: ArkitektServerConfig):
    """Generate the full hubinator deployment (services + local coordinator).

    This is the all-in-one generator: data/compute services PLUS a local Lok
    coordinator (when ``lok.enabled``). ``hub`` and ``coord`` deployments use the
    dedicated ``write_hub_files`` / ``write_coord_files`` below instead.
    """
    ctx = GenContext.from_server_config(config)
    all_services = iterate_service(config)  # enabled services, includes lok
    data_services = [s for s in all_services if s.get_identifier() != "lok"]

    services: Dict[str, Any] = {}
    redeem_tokens: list[RedeemTokenConfig] = []

    _provision_org_bots(ctx)
    _emit_infrastructure(ctx, all_services, tmpdir, services)
    _emit_deployer(ctx, services, redeem_tokens)
    _emit_apps(ctx, services, redeem_tokens)
    _emit_data_services(ctx, data_services, tmpdir, services)
    _emit_gateway(ctx, all_services, tmpdir, services)
    if ctx.lok_enabled:
        _emit_lok(ctx, all_services, tmpdir, services, redeem_tokens)
    _finalize_compose(ctx, services, tmpdir)


def write_hub_files(tmpdir: Path, config: "HubConfig") -> None:
    """Generate a hub deployment: data/compute services, NO local coordinator.

    Auth is delegated to the remote ``coord_server`` (see ``build_authentikate``):
    no Lok container, no ``/.well-known`` route, and no organizations/users are
    provisioned.
    """
    ctx = GenContext.from_hub_config(config)
    data_services = iterate_services(
        [
            config.rekuest,
            config.kabinet,
            config.mikro,
            config.fluss,
            config.elektro,
            config.alpaka,
            config.kraph,
        ]
    )

    services: Dict[str, Any] = {}

    _emit_infrastructure(ctx, data_services, tmpdir, services)
    _emit_data_services(ctx, data_services, tmpdir, services)
    _emit_gateway(ctx, data_services, tmpdir, services)
    _finalize_compose(ctx, services, tmpdir)


def write_coord_files(tmpdir: Path, config: "CoordConfig") -> None:
    """Generate a coordinator deployment: Lok (+ Kontrol frontend) and deps only.

    Emits Lok, the Caddy gateway, and Lok's Postgres/Redis/MinIO dependencies,
    plus the Lok provisioning (organizations/users/memberships/admin/kommunity).
    No data/compute services and no deployer.
    """
    ctx = GenContext.from_coord_config(config)
    lok_services = iterate_services([config.lok])  # [lok] when enabled

    services: Dict[str, Any] = {}
    redeem_tokens: list[RedeemTokenConfig] = []

    _provision_org_bots(ctx)
    _emit_infrastructure(ctx, lok_services, tmpdir, services)
    _emit_gateway(ctx, lok_services, tmpdir, services)
    if ctx.lok_enabled:
        _emit_lok(ctx, lok_services, tmpdir, services, redeem_tokens)
    _finalize_compose(ctx, services, tmpdir)


def write_engine_files(tmpdir: Path, config: "EngineConfig") -> None:
    """Generate a standalone engine deployment: just the deployer.

    Emits a self-contained ``docker-compose.yaml`` with a single deployer service
    that connects to an existing Arkitekt deployment (``config.url``) and joins its
    (external) docker network to orchestrate app containers on its behalf.
    """
    deployer = config.deployer

    services: Dict[str, Any] = {
        deployer.host: {
            "image": deployer.image,
            "volumes": ["/var/run/docker.sock:/var/run/docker.sock"],
            "command": (
                f"arkitekt-next app run prod --redeem-token={deployer.redeem_token} "
                f"--url {config.url}"
            ),
            "stop_grace_period": f"{config.default_service_grace_period_seconds}s",
            "networks": [config.network, "default"],
            "deploy": {
                "restart_policy": {
                    "condition": "on-failure",
                    "delay": "10s",
                    "max_attempts": 10,
                    "window": "300s",
                }
            },
            "environment": {
                "ARKITEKT_GATEWAY": config.url,
                "ARKITEKT_NETWORK": config.network,
                "ARKITEKT_DEVICE_ID": config.device_id,
                "INSTANCE_ID": config.instance_id,
                "DEPLOYER_ORGANIZATION": config.organization,
            },
        }
    }

    docker_compose_content: Dict[str, Any] = {
        "services": services,
        # The target deployment owns the network; the engine joins it as external.
        "networks": {config.network: {"external": True}},
    }

    (tmpdir / "docker-compose.yaml").write_text(
        yaml.dump(docker_compose_content, default_flow_style=False)
    )


def collect_all_files(base: Path) -> dict[Path, Path]:
    """
    Recursively collect all files in a directory tree.
    This function scans the specified directory and returns a dictionary
    mapping relative file paths to their absolute Path objects. It is useful
    for comparing directory structures or preparing for deployment.

    Args:
        base: The base directory to scan

    Returns:
        A dictionary mapping relative paths to absolute Path objects
    """
    files: dict[Path, Path] = {}
    for path in base.rglob("*"):
        if path.is_file():
            relative_path = path.relative_to(base)
            files[relative_path] = path
    return files


def compare_filesystems(
    virtual_dir: Path, real_dir: Path, *, allow_deletes: bool = True
):
    """
    Compare virtual and real directory structures and display differences.

    This function performs a comprehensive comparison between the generated
    (virtual) configuration files and the existing (real) deployment files.
    It identifies files that would be:
    - Created (exist in virtual but not real)
    - Deleted (exist in real but not virtual, if allow_deletes=True)
    - Modified (exist in both but with different content)

    For modified files, it displays a unified diff showing the exact changes.

    Args:
        virtual_dir: Directory containing the generated configuration files
        real_dir: Directory containing the existing deployment files
        allow_deletes: Whether to report files that would be deleted
    """
    virtual_files = collect_all_files(virtual_dir)
    real_files = collect_all_files(real_dir)

    all_paths = sorted(set(virtual_files) | set(real_files))

    for path in all_paths:
        v_file = virtual_files.get(path)
        r_file = real_files.get(path)

        if v_file and not r_file:
            print(f"[+] Would create: {path}")
        elif not v_file and r_file:
            if allow_deletes:
                print(f"[-] Would delete: {path}")
        elif v_file and r_file:
            v_lines = v_file.read_text().splitlines(keepends=True)
            r_lines = r_file.read_text().splitlines(keepends=True)

            if v_lines != r_lines:
                diff = list(
                    difflib.unified_diff(
                        r_lines,
                        v_lines,
                        fromfile=f"{path} (current)",
                        tofile=f"{path} (new)",
                        lineterm="",
                    )
                )
                print(f"[~] Would modify: {path}")
                print("".join(diff))


def run_dry_run_diff(
    config: ArkitektServerConfig,
    real_dir: Path,
    allow_deletes: bool = False,
    yes: bool = False,
):
    """
    Execute a dry-run comparison and optionally apply changes.

    This is the main entry point for the configuration diff workflow. It:
    1. Creates a temporary directory with the generated configuration
    2. Compares it to the existing deployment directory
    3. Shows the user what changes would be made
    4. Prompts for confirmation before applying changes
    5. Copies the new configuration files if confirmed

    This provides a safe way to preview and apply configuration changes
    without accidentally overwriting important files.

    Args:
        config: The Arkitekt server configuration to deploy
        real_dir: The target directory for the deployment files
        allow_deletes: Whether to allow deletion of existing files

    Raises:
        click.Abort: If the user declines to apply the changes
    """

    with tempfile.TemporaryDirectory() as tmp:
        virtual_dir = Path(tmp)
        print(f"🛠  Generating virtual config in: {virtual_dir}")
        write_virtual_config_files(virtual_dir, config)

        print(f"\n🔍 Comparing to real directory: {real_dir}\n")
        compare_filesystems(virtual_dir, real_dir, allow_deletes=allow_deletes)

        if not yes:
            from arkitekt_next.cli.interactive import require_interactive

            require_interactive(
                "Confirming the config changes",
                hint="Pass yes=True (or the command's --yes flag) to apply non-interactively.",
            )
            click.confirm(
                "Do you want to apply these changes?",
                abort=True,
            )

        # copy the virtual files to the real directory
        for path in virtual_dir.rglob("*"):
            if path.is_file():
                relative_path = path.relative_to(virtual_dir)
                target_path = real_dir / relative_path
                target_path.parent.mkdir(parents=True, exist_ok=True)
                with open(path, "r") as src_file:
                    with open(target_path, "w") as dst_file:
                        dst_file.write(src_file.read())
