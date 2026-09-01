from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, Generator, Literal, cast
from arkitekt_next.server.diff import (
    write_virtual_config_files,
    write_hub_files,
    write_coord_files,
    write_engine_files,
)
from .config import ArkitektServerConfig, HubConfig, CoordConfig, EngineConfig
from .services import SERVICE_REGISTRY
from pathlib import Path
from pydantic import BaseModel
from dokker import Deployment, testing
from dataclasses import dataclass

if TYPE_CHECKING:
    from dokker import LogWatcher

    from arkitekt_next.server.lok import LokController

# Services that are always enabled regardless of the requested selection.
# Lok provides authentication/authorization and every other service depends on it.
REQUIRED_SERVICES = {"lok"}

# Release channels that select the image tag for the Arkitekt services.
Channel = Literal["next", "latest"]


def _retag_image(image: str, tag: str) -> str:
    """Replace the tag of a docker image reference, preserving registry/repository.

    ``jhnnsrs/mikro:dev`` -> ``jhnnsrs/mikro:<tag>``. If the image has no tag, one
    is appended. A ``:`` in a registry host (e.g. ``host:5000/img``) is ignored.
    """
    # Only treat a colon in the final path segment as a tag separator.
    if ":" in image.rsplit("/", 1)[-1]:
        base = image.rsplit(":", 1)[0]
    else:
        base = image
    return f"{base}:{tag}"


def create_server(path: Path | str, config: ArkitektServerConfig | None = None):
    """
    Create a server configuration at the specified path using the provided config.

    Args:
        path (str): The path where the server configuration will be created.
        config (ArkitektServerConfig): The configuration for the server.

    Returns:
        None
    """
    if isinstance(path, str):
        path = Path(path)

    # Ensure the directory exists
    path.mkdir(parents=True, exist_ok=True)

    if config is None:
        config = ArkitektServerConfig()

    # Write the configuration to a file
    write_virtual_config_files(path, config)


def create_hub_server(path: Path | str, config: HubConfig | None = None) -> None:
    """Generate a hub deployment (services, no local coordinator) at ``path``."""
    if isinstance(path, str):
        path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    if config is None:
        config = HubConfig()
    write_hub_files(path, config)


def create_coord_server(path: Path | str, config: CoordConfig | None = None) -> None:
    """Generate a coordinator deployment (Lok + Kontrol only) at ``path``."""
    if isinstance(path, str):
        path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    if config is None:
        config = CoordConfig()
    write_coord_files(path, config)


def create_engine_server(path: Path | str, config: EngineConfig | None = None) -> None:
    """Generate a standalone engine (deployer) deployment at ``path``."""
    if isinstance(path, str):
        path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    if config is None:
        config = EngineConfig()
    write_engine_files(path, config)


def free_ports(count: int = 1) -> list[int]:
    """Ask the OS for ``count`` *distinct* currently-free TCP ports.

    Preferred over picking random numbers in a range: two deployments started at
    the same time (``pytest-xdist``, or a test running while a dev stack is up)
    would otherwise collide often enough to be flaky.

    Every socket is held open until all of them are bound -- binding and releasing
    one at a time lets the OS hand out the same port twice, which would then fail
    at ``docker compose up``.

    There is still an unavoidable race (the ports are released when this returns
    and only re-bound when docker starts), but the window is small and far better
    than a blind ``randint``.
    """
    import socket
    from contextlib import ExitStack

    with ExitStack() as stack:
        sockets = [
            stack.enter_context(socket.socket(socket.AF_INET, socket.SOCK_STREAM))
            for _ in range(count)
        ]
        for sock in sockets:
            sock.bind(("", 0))
        return [int(sock.getsockname()[1]) for sock in sockets]


def create_test_config(
    services: list[str] | None = None,
    *,
    kind: str = "hubinator",
    config: BaseModel | None = None,
    channel: Channel | None = None,
    randomize_ports: bool = True,
) -> BaseModel:
    """Build a deployment config suitable for ephemeral/test deployments.

    Enables only the requested services (plus the always-required ones, see
    ``REQUIRED_SERVICES``) and disables the rest. Also hardens the config for
    throwaway use: the database and object store become anonymous docker volumes
    rather than bind mounts, and the exposed gateway ports are picked from the
    free-port pool so several deployments can run side by side.

    The four kinds are genuinely different schemas -- a ``HubConfig`` has no
    ``deployer`` and no ``lok``, a ``CoordConfig`` has no data services, an
    ``EngineConfig`` has neither storage nor a gateway -- so every step below is
    gated on the declared shape in ``KINDS[kind]`` rather than probed with
    ``hasattr``.

    Args:
        services: Identifiers of the services to enable (e.g. ``["rekuest", "mikro"]``).
            Must be keys of ``SERVICE_REGISTRY``, and must exist on this kind's schema.
            If ``None``, the config's existing enabled flags are left untouched.
        kind: Deployment kind; a key of ``KINDS``.
        config: A base config to mutate. A fresh one of the kind's class is created
            if not provided.
        channel: Release channel selecting the service image tag -- ``"next"`` or
            ``"latest"`` retags every Arkitekt service image accordingly. If ``None``
            (the default), each service keeps its configured image/version.
        randomize_ports: Whether to assign free exposed gateway ports.

    Returns:
        The configured deployment config.
    """
    from arkitekt_next.server.deployments import DEPLOYMENTS
    from arkitekt_next.server.kinds import KINDS

    meta = KINDS[kind]
    config = config if config is not None else DEPLOYMENTS[kind].config_cls()

    if services is not None:
        unknown = set(services) - set(SERVICE_REGISTRY)
        if unknown:
            raise ValueError(
                f"Unknown service(s): {sorted(unknown)}. "
                f"Available services: {sorted(SERVICE_REGISTRY)}"
            )

        # A service can be valid but absent from this kind's schema (asking a coord
        # for `mikro`, say). That is a test-authoring mistake worth naming.
        missing = {s for s in services if not hasattr(config, s)}
        if missing:
            raise ValueError(
                f"The '{kind}' deployment has no service(s): {sorted(missing)}. "
                f"It carries: {sorted(s for s in SERVICE_REGISTRY if hasattr(config, s))}"
            )

        wanted = set(services) | REQUIRED_SERVICES
        for name in SERVICE_REGISTRY:
            service = getattr(config, name, None)
            if service is not None:
                service.enabled = name in wanted

    if channel is not None:
        # Switch every Arkitekt service image to the requested release channel.
        # Some services (e.g. lovekit) have no configurable image and are skipped.
        for name in SERVICE_REGISTRY:
            service = getattr(config, name, None)
            if service is not None and getattr(service, "image", None) is not None:
                service.image = _retag_image(service.image, channel)

    # The four schemas genuinely differ in which blocks they carry, so the presence
    # of each is asserted by ``KINDS[kind]`` above rather than by the type system.
    cfg: Any = config

    # The deployer needs the docker socket and registers itself against a running
    # gateway; it is irrelevant for service tests and only adds a crash-looping
    # container, so disable it for throwaway deployments.
    if meta.has_deployer:
        cfg.deployer.enabled = False

    # Make sure we are creating volumes not bind mounts, so nothing lingers on disk.
    if meta.has_storage:
        cfg.minio.mount = None
        cfg.db.mount = None

    if randomize_ports and meta.has_gateway:
        # Both in one call, so the two ports cannot come back identical.
        http_port, https_port = free_ports(2)
        cfg.gateway.exposed_http_port = http_port
        cfg.gateway.exposed_https_port = https_port

    return config


@contextmanager
def temp_server(
    config: BaseModel | None = None,
) -> Generator[Path, None, None]:
    """
    Create a temporary server configuration using the provided config.

    This is a context manager that yields the path to the temporary server configuration.
    The server directory is created and cleaned up automatically.

    Attention: The docker compose project that was created will not be cleaned up automatically.
                If you want to clean it up, you have to call `down` on the project manually.
                Or use the `local` function from the `dokker` package to create a local deployment.

    Args:
        config (ArkitektServerConfig): The configuration for the server.

    Yield:
        Path: The path to the temporary server configuration.
    """
    import tempfile

    # ``temp_server`` predates the kind-aware API and only ever built the full stack.
    config = cast(ArkitektServerConfig, create_test_config(config=config))

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        create_server(temp_path, config)
        yield temp_path


@dataclass
class ArkitektServer:
    """Handle to a generated Arkitekt deployment for use in tests.

    Wraps the generated config, the directory it was written to and a (not yet
    started) ``dokker`` deployment with health checks pre-registered for every
    enabled web service. The caller is responsible for the docker lifecycle::

        with srv.setup:
            srv.setup.up()
            srv.setup.check_health()
            ...
    """

    config: BaseModel
    deployment: Deployment
    path: Path
    #: Which deployment kind was generated (a key of ``KINDS``).
    kind: str = "hubinator"

    @property
    def setup(self) -> Deployment:
        """The underlying ``dokker`` deployment (alias for ``deployment``)."""
        return self.deployment

    @property
    def enabled_services(self) -> list[str]:
        """Identifiers of the services actually deployed (enabled and deployable).

        Kind-agnostic -- e.g. ``lovekit`` is enabled by default but has no image and
        is not deployed, so it is never listed; a coord lists only ``lok``.
        """
        from arkitekt_next.server.lifecycle import health_services

        return [service.get_identifier() for service in health_services(self.config)]

    def watch(self, *services: str) -> "LogWatcher":
        """Capture ``services``' container logs for the duration of a ``with`` block.

        When an assertion inside the block fails, dokker appends those logs to the
        traceback. Without it a failing integration test reports only the symptom
        ("got 500") and none of the server-side reason::

            with server.watch("mikro", "lok"):
                assert upload_something()

        Passing no service names watches every deployed web service.
        """
        names = list(services) if services else self.enabled_services
        return self.deployment.create_watcher(
            services=names,
            append_to_traceback=True,
            rich_traceback=True,
            wait_for_first_log=False,
        )

    def get_service_url(
        self, service_name: str, internal_port: int = 80, protocol: str = "http"
    ) -> str:
        """Get the URL for a service."""
        service = self.deployment.spec.find_service(service_name)
        if not service:
            raise ValueError(f"Service {service_name} not found")

        port = service.get_port_for_internal(internal_port)
        if not port:
            raise ValueError(
                f"Service {service_name} does not expose internal port {internal_port}"
            )

        return f"{protocol}://localhost:{port.published}"

    @property
    def gateway_url(self) -> str:
        """Get the URL for the gateway service."""
        return self.get_service_url("gateway", 80)

    @property
    def lok(self) -> "LokController":
        """Controller for the deployment's lok (coordination) server.

        Lets tests act as the human operator: approve/deny device codes,
        authorize hub registrations, or run arbitrary management
        commands inside the lok container.
        """
        from arkitekt_next.server.lok import LokController

        return LokController(self.deployment)

    def health_url(self, service: str) -> str:
        """Get the gateway-routed health-check URL for a service (``/<service>/ht``)."""
        return f"{self.gateway_url}/{service}/ht"

    def graphql_url(self, service: str) -> str:
        """Get the gateway-routed GraphQL endpoint URL for a service."""
        return f"{self.gateway_url}/{service}/graphql"


# Backwards-compatibility alias for the previous name.
TempDeployment = ArkitektServer


def _register_health_checks(setup: Deployment, config: BaseModel) -> None:
    """Register a gateway-routed ``/<host>/ht`` health check per enabled web service.

    Delegates to :func:`arkitekt_next.server.lifecycle.register_health_checks`, which
    the CLI's ``status`` command uses too -- so a stack is judged healthy by exactly
    the same criteria whether a test or a human asks.
    """
    from arkitekt_next.server.lifecycle import register_health_checks

    register_health_checks(setup, config)


@contextmanager
def temp_setup(
    services: list[str] | None = None,
    *,
    kind: str = "hubinator",
    config: BaseModel | None = None,
    channel: Channel | None = None,
    health_checks: bool = True,
) -> Generator[ArkitektServer, None, None]:
    """Generate a temporary Arkitekt deployment of any kind and yield a handle to it.

    The configuration is written to a temporary directory and a ``dokker`` testing
    deployment is built with health checks registered for every enabled web service.
    The deployment is **not** started -- the caller decides when to ``up()``/``down()``.
    The temporary directory is removed when the context exits, and the ``testing``
    teardown policy ensures the docker compose project is torn down if it was started.

    Args:
        services: Identifiers of the services to enable. See ``create_test_config``.
        kind: Which deployment kind to generate -- a key of ``KINDS``. Defaults to
            ``"hubinator"`` (the full stack), which is what this used to hardcode.
            ``"engine"`` generates fine but cannot be started on its own: it is a lone
            deployer joining an existing deployment's external network.
        config: An optional base config to mutate.
        channel: Release channel for the service images (``"next"``/``"latest"``/``None``).
        health_checks: Register per-service health checks on the deployment.

    Yield:
        ArkitektServer: A handle exposing the config, path, and dokker ``setup``.
    """
    import tempfile

    from arkitekt_next.server.deployments import DEPLOYMENTS

    spec = DEPLOYMENTS[kind]
    config = create_test_config(services, kind=kind, config=config, channel=channel)

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        # Each kind has its own generator; ``create_server`` is only the hubinator one.
        spec.generator(temp_path, config)

        # ``testing`` defaults to the "testing" teardown policy, which already
        # downs the stack (removing volumes/orphans) and tears the project down
        # on context exit -- no explicit down_on_exit flag is needed.
        setup = testing(temp_path / "docker-compose.yaml")

        if health_checks:
            _register_health_checks(setup, config)

        yield ArkitektServer(config=config, deployment=setup, path=temp_path, kind=kind)
