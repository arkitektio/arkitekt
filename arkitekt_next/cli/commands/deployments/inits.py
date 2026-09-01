"""Per-kind ``init`` commands.

Unlike the lifecycle verbs (which are identical across kinds and therefore built by
factories in :mod:`.commands`), each kind's ``init`` genuinely asks for different
things: a hub needs a coordination server, a coordinator does not; an engine takes a
redeem token and no template at all. So these stay four explicit functions -- but
they share every common option through :mod:`arkitekt_next.cli.options`, which is
what used to be copy-pasted.

``INITS`` maps a kind name to its command function; :mod:`.main` mounts them.
"""

import typer

from arkitekt_next.cli.options import (
    BackendOption,
    PathArgument,
    PortOption,
    RekuestServerOption,
    ServicesOption,
    SslPortOption,
    TemplateOption,
    UseDefaultOption,
    WizardOption,
)
from arkitekt_next.cli.vars import get_console
from arkitekt_next.cli.commands._server_common import (
    finalize,
    resolve_path,
    select_config,
    set_enabled_services,
)


def _apply_ports(config, port, ssl_port) -> None:
    """Apply the shared gateway port overrides, when given."""
    if port is not None:
        config.gateway.exposed_http_port = port
    if ssl_port is not None:
        config.gateway.exposed_https_port = ssl_port


def hub_init(
    ctx: typer.Context,
    path: PathArgument = None,
    template: TemplateOption = None,
    wizard: WizardOption = False,
    use_default: UseDefaultOption = False,
    services: ServicesOption = [],
    coord_server: str = typer.Option(
        None,
        "--coord-server",
        help="External coordination (auth) server whose JWKS the services trust.",
    ),
    rekuest_server: RekuestServerOption = None,
    port: PortOption = None,
    ssl_port: SslPortOption = None,
    backend: BackendOption = "docker",
) -> None:
    """Initialize a hub configuration (services, no local coordinator).

    A hub never asks about organizations or users -- only about the local
    servers/services. Explicit options override the wizard/template defaults.
    """
    from arkitekt_next.server.deployments import DEPLOYMENTS

    spec = DEPLOYMENTS["hub"]
    console = get_console(ctx)
    target = resolve_path(ctx, path)

    config = select_config(
        spec, console, wizard=wizard, template=template, use_default=use_default
    )

    # Explicit CLI options override wizard/template defaults (only when provided).
    if services:
        set_enabled_services(config, services)
    if coord_server is not None:
        config.coord_server = coord_server
    if rekuest_server is not None:
        config.rekuest_server = rekuest_server
        config.rekuest.enabled = rekuest_server == "local"
    _apply_ports(config, port, ssl_port)

    console.print(
        f"Creating [bold]hub[/bold] ({template or 'wizard'}) trusting coordinator "
        f"[cyan]{config.coord_server}[/cyan] at [cyan]{target}[/cyan]..."
    )
    finalize(ctx, target, config, spec, template=template, backend=backend)


def coord_init(
    ctx: typer.Context,
    path: PathArgument = None,
    template: TemplateOption = None,
    wizard: WizardOption = False,
    use_default: UseDefaultOption = False,
    port: PortOption = None,
    ssl_port: SslPortOption = None,
    backend: BackendOption = "docker",
) -> None:
    """Initialize a coordinator configuration (Lok + Kontrol only).

    With no `--template`, the interactive wizard runs and asks whether to set up
    organizations. Passing a `--template` or `--default` skips all questioning
    and uses defaults.
    """
    from arkitekt_next.server.deployments import DEPLOYMENTS

    spec = DEPLOYMENTS["coord"]
    console = get_console(ctx)
    target = resolve_path(ctx, path)

    config = select_config(
        spec, console, wizard=wizard, template=template, use_default=use_default
    )
    _apply_ports(config, port, ssl_port)

    console.print(
        f"Creating [bold]coordinator[/bold] ({template or 'wizard'}) with Lok + Kontrol "
        f"at [cyan]{target}[/cyan]..."
    )
    finalize(ctx, target, config, spec, template=template, backend=backend)


def hubinator_init(
    ctx: typer.Context,
    path: PathArgument = None,
    template: TemplateOption = None,
    wizard: WizardOption = False,
    use_default: UseDefaultOption = False,
    services: ServicesOption = [],
    rekuest_server: RekuestServerOption = "local",
    port: PortOption = None,
    ssl_port: SslPortOption = None,
    backend: BackendOption = "docker",
) -> None:
    """Initialize a full hub+coordinator configuration."""
    from arkitekt_next.server.deployments import DEPLOYMENTS

    spec = DEPLOYMENTS["hubinator"]
    console = get_console(ctx)
    target = resolve_path(ctx, path)

    config = select_config(
        spec, console, wizard=wizard, template=template, use_default=use_default
    )

    if services:
        set_enabled_services(config, services)
    _apply_ports(config, port, ssl_port)

    # A hubinator runs the coordinator locally: Lok is enabled and the services
    # trust it. This is the default full-stack deployment.
    config.coord_server = "local"
    config.lok.enabled = True

    if rekuest_server is not None:
        config.rekuest_server = rekuest_server
        config.rekuest.enabled = rekuest_server == "local"

    console.print(
        f"Creating [bold]hubinator[/bold] ({template or 'wizard'}) full stack "
        f"(hub + coordinator) at [cyan]{target}[/cyan]..."
    )
    finalize(ctx, target, config, spec, template=template, backend=backend)


def engine_init(
    ctx: typer.Context,
    path: PathArgument = None,
    url: str = typer.Option(
        None, "--url", help="Gateway URL of the Arkitekt deployment to connect to."
    ),
    redeem_token: str = typer.Option(
        None, "--redeem-token", help="Redeem token issued by the target deployment."
    ),
    network: str = typer.Option(
        None,
        "--network",
        help="Docker network to join (the target deployment's internal network).",
    ),
    organization: str = typer.Option(
        None, "--organization", help="Organization the deployer acts on behalf of."
    ),
    instance_id: str = typer.Option(
        None, "--instance-id", help="Instance ID for the deployer."
    ),
    backend: BackendOption = "docker",
) -> None:
    """Initialize a standalone engine (deployer) configuration."""
    from arkitekt_next.server.config import EngineConfig
    from arkitekt_next.server.deployments import DEPLOYMENTS

    spec = DEPLOYMENTS["engine"]
    console = get_console(ctx)
    target = resolve_path(ctx, path)

    # Engine has no wizard and no templates -- build the default config and apply
    # the explicit options on top.
    config = EngineConfig()
    if url is not None:
        config.url = url
    if network is not None:
        config.network = network
    if organization is not None:
        config.organization = organization
    if instance_id is not None:
        config.instance_id = instance_id
    if redeem_token is not None:
        config.deployer.redeem_token = redeem_token

    console.print(
        f"Creating [bold]engine[/bold] (deployer) connecting to [cyan]{config.url}[/cyan] "
        f"at [cyan]{target}[/cyan]..."
    )
    finalize(ctx, target, config, spec, template=None, backend=backend)


#: Kind name -> its ``init`` command function.
INITS = {
    "hub": hub_init,
    "coord": coord_init,
    "hubinator": hubinator_init,
    "engine": engine_init,
}
