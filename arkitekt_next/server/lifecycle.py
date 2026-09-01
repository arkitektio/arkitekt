"""Docker lifecycle for generated Arkitekt deployments, backed by ``dokker``.

Both the CLI (``hub up``, ``coord down``, ``hubinator status``, ...) and the test
fixtures in :mod:`arkitekt_next.server.dev` drive deployments through this module,
so a stack behaves the same whether a human starts it or a test does.

This replaces the raw ``docker compose`` subprocess calls that used to live in
:mod:`arkitekt_next.server.runner`. A dokker ``Deployment`` gives us the compose
spec (and therefore the actually-published ports), health checks and log
streaming for free -- none of which a bare ``subprocess.run`` could offer.

Everything here imports ``dokker`` lazily: it ships in the optional ``server``
extra, and the base CLI must stay importable without it.
"""

from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, List, Optional, Tuple

from pydantic import BaseModel

if TYPE_CHECKING:
    from dokker import Deployment

    from arkitekt_next.server.config import BaseService

#: Name of the compose file every generator writes into the deployment directory.
COMPOSE_FILENAME = "docker-compose.yaml"

#: Internal port the gateway (Caddy) listens on inside the compose network. Every
#: service is reached from the host as ``<gateway published port>/<service host>``.
GATEWAY_INTERNAL_PORT = 80

#: Health-check tuning. A first boot runs database migrations for every Django
#: service, which comfortably exceeds any default.
HEALTH_TIMEOUT = 10
HEALTH_MAX_RETRIES = 60


class ConsoleLogger:
    """Render docker compose output as plain dimmed lines.

    Implements dokker's ``Logger`` protocol. dokker's own ``PrintLogger`` prints the
    raw ``(stream, line)`` tuple -- i.e. ``('STDERR', 'Container x Started')`` --
    which is noisy in a CLI. This prints just the message.
    """

    def __init__(self, printer: Optional[Callable[[str], None]] = None) -> None:
        self.printer = printer or print

    def _emit(self, log: Any) -> None:
        # dokker hands us (stream, line); tolerate a bare string too.
        message = log[1] if isinstance(log, (tuple, list)) and len(log) > 1 else log
        text = str(message).rstrip()
        if text:
            self.printer(text)

    # The protocol's five hooks all render the same way.
    on_pull = on_up = on_stop = on_logs = on_down = _emit


def compose_path(path: Path | str) -> Path:
    """Path of the generated compose file inside a deployment directory."""
    return Path(path) / COMPOSE_FILENAME


def gateway_health_url(spec: Any, host: str) -> str:
    """Gateway-routed health URL (``/<host>/ht``) for a service, from a compose spec.

    ``spec`` is a dokker ``ComposeSpec``; the published gateway port is only known
    after the deployment has been inspected, which is why this is resolved lazily
    by the health check rather than baked in at registration time.
    """
    gateway = spec.find_service("gateway")
    if gateway is None:
        raise ValueError("The deployment has no 'gateway' service to route health checks through.")
    port = gateway.get_port_for_internal(GATEWAY_INTERNAL_PORT)
    if port is None:
        raise ValueError(
            f"The gateway does not publish its internal port {GATEWAY_INTERNAL_PORT}."
        )
    return f"http://localhost:{port.published}/{host}/ht"


def health_services(config: BaseModel) -> List["BaseService"]:
    """Enabled web services of any deployment config, in a stable order.

    Shape-agnostic on purpose: ``HubConfig`` carries no ``lok`` and ``CoordConfig``
    carries no data services, so the full-config-only ``iterate_service`` would
    raise ``AttributeError`` on them.
    """
    from arkitekt_next.server.diff import iterate_any_service

    return iterate_any_service(config)


def register_health_checks(
    deployment: "Deployment",
    config: BaseModel,
    *,
    timeout: int = HEALTH_TIMEOUT,
    max_retries: int = HEALTH_MAX_RETRIES,
) -> List[str]:
    """Register a gateway-routed ``/<host>/ht`` health check per enabled web service.

    Returns the service hosts that got a check, so callers can report what will be
    probed. An engine deployment has no gateway and no web services, so it gets
    none -- that is expected, not an error.
    """
    hosts = []
    for service in health_services(config):
        host = service.host
        # Bind ``host`` per-iteration: a bare closure would capture the loop
        # variable and make every check probe the last service.
        deployment.add_health_check(
            url=lambda spec, host=host: gateway_health_url(spec, host),
            service=host,
            timeout=timeout,
            max_retries=max_retries,
        )
        hosts.append(host)
    return hosts


def load_config(path: Path | str, kind: str) -> BaseModel:
    """Load the profile YAML for ``kind`` out of a deployment directory.

    Raises ``FileNotFoundError`` if the deployment was never initialized.
    """
    from arkitekt_next.server.deployments import DEPLOYMENTS
    from arkitekt_next.server.utils import load_profile_yaml

    spec = DEPLOYMENTS[kind]
    config_path = Path(path) / spec.filename
    config, _backend = load_profile_yaml(str(config_path), spec.config_cls)
    return config


def open_deployment(
    path: Path | str,
    kind: str,
    *,
    config: Optional[BaseModel] = None,
    with_health: bool = True,
    verbose: bool = True,
    printer: Optional[Callable[[str], None]] = None,
) -> Tuple["Deployment", BaseModel]:
    """Open a *generated* deployment directory as a dokker deployment.

    Uses the ``manual`` teardown policy deliberately. The CLI's verbs are explicit:
    ``up`` must leave the stack running after the command exits, and ``down`` is the
    only thing that stops it. The ``local`` policy would *stop* the stack when the
    context manager exits -- i.e. ``up`` would start and immediately stop it.
    (Tests use :func:`arkitekt_next.server.dev.temp_setup` with the ``testing``
    policy instead: unique project name, and volumes removed on down.)

    The returned deployment **must be entered** before calling any of its sync
    methods -- dokker's sync API is ``unkoil``-backed and raises "No koil context
    found" outside a ``with`` block::

        deployment, config = open_deployment(path, kind)
        with deployment:
            deployment.up()

    Args:
        path: Directory holding ``docker-compose.yaml`` and the profile YAML.
        kind: Deployment kind, a key of ``DEPLOYMENTS``.
        config: Pre-loaded config; loaded from the profile YAML when omitted.
        with_health: Register per-service health checks.
        verbose: Stream docker compose output instead of swallowing it.
        printer: Where verbose output goes. Defaults to ``print``.

    Returns:
        The (not yet started) deployment and the config it was built from.
    """
    from dokker import local

    target = Path(path)
    compose = compose_path(target)
    if not compose.exists():
        raise FileNotFoundError(compose)

    if config is None:
        config = load_config(target, kind)

    deployment = local(compose, policy="manual")
    if verbose:
        # dokker defaults to a VoidLogger, which silently swallows all compose
        # output -- unhelpful for a CLI where pulls take minutes.
        deployment.logger = ConsoleLogger(printer)

    if with_health:
        register_health_checks(deployment, config)

    return deployment, config
