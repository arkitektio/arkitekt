import rich_click as click

from arkitekt_next.cli.docs import HUBINATOR_DOCS, help_epilog
from arkitekt_next.cli.vars import get_console
from arkitekt_next.cli.commands._server_common import (
    finalize,
    make_up_command,
    require_server_deps,
    resolve_path,
    select_config,
    set_enabled_services,
)


@click.group(epilog=help_epilog(HUBINATOR_DOCS))
@click.pass_context
def hubinator(ctx) -> None:
    """Run the full stack: a hub AND a local coordinator in one deployment.

    A hubinator is a self-contained Arkitekt instance -- the data/compute
    services plus a local Lok coordinator (with Kontrol frontend) and, optionally,
    a deployer. This is the all-in-one deployment the standalone arkitekt-server
    tool produced by default. Use `hubinator init` then `hubinator up`.
    """
    require_server_deps()


@hubinator.command()
@click.argument("path", required=False)
@click.option("--template", "-t", default="default", help="Config template (stable, dev, default, minimal).")
@click.option("--wizard", "-w", is_flag=True, help="Run the interactive configuration wizard.")
@click.option("--default", "-d", "use_default", is_flag=True, help="Accept all defaults (skip the wizard, no prompts).")
@click.option(
    "--service",
    "-s",
    "services",
    multiple=True,
    help="Enable exactly these services (repeatable). Defaults to the template's selection.",
)
@click.option(
    "--rekuest-server",
    default="local",
    help="Rekuest (provenance) server host ('local' runs rekuest as a core dependency).",
)
@click.option("--port", type=int, default=None, help="Exposed HTTP port.")
@click.option("--ssl-port", type=int, default=None, help="Exposed HTTPS port.")
@click.option("--backend", default="docker", help="Deployment backend (docker, podman, kubernetes).")
@click.pass_context
def init(ctx, path, template, wizard, use_default, services, rekuest_server, port, ssl_port, backend) -> None:
    """Initialize a full hub+coordinator configuration."""
    from arkitekt_next.server.deployments import DEPLOYMENTS

    spec = DEPLOYMENTS["hubinator"]
    console = get_console(ctx)
    target = resolve_path(ctx, path)

    config = select_config(spec, console, wizard=wizard, template=template, use_default=use_default)

    if services:
        set_enabled_services(config, services)

    if port is not None:
        config.gateway.exposed_http_port = port
    if ssl_port is not None:
        config.gateway.exposed_https_port = ssl_port

    # A hubinator runs the coordinator locally: Lok is enabled and the services
    # trust it. This is the default full-stack deployment.
    config.coord_server = "local"
    config.lok.enabled = True

    config.rekuest_server = rekuest_server
    config.rekuest.enabled = rekuest_server == "local"

    console.print(
        f"Creating [bold]hubinator[/bold] ({template}) full stack (hub + coordinator) "
        f"at [cyan]{target}[/cyan]..."
    )
    finalize(ctx, target, config, spec, template=template, backend=backend)


hubinator.add_command(
    make_up_command(
        "hubinator",
        help="Compose the full stack (services + coordinator + auth) and run `docker compose up`.",
    ),
    "up",
)
