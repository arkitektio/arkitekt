import rich_click as click

from arkitekt_next.cli.docs import HUB_DOCS, help_epilog
from arkitekt_next.cli.vars import get_console
from arkitekt_next.cli.commands._server_common import (
    finalize,
    make_up_command,
    require_server_deps,
    resolve_path,
    select_config,
    set_enabled_services,
)
from arkitekt_next.cli.commands.hub.connect import connect


@click.group(epilog=help_epilog(HUB_DOCS))
@click.pass_context
def hub(ctx) -> None:
    """Run a hub: a stack of Arkitekt services WITHOUT a local coordinator.

    A hub bundles the data/compute services (rekuest, mikro, fluss, ...) and
    trusts an external coordination (auth) server for identity. It manages no
    organizations or users, and comes with no deployer. Use `hub init` to write
    the config, `hub up` to compose and start the stack, and `hub connect` to
    register the hub's services with an organization. If you also want to run the
    coordinator locally, use `hubinator` instead.
    """
    require_server_deps()


@hub.command()
@click.argument("path", required=False)
@click.option(
    "--template",
    "-t",
    default=None,
    help="Config template (stable, dev, default, minimal). If omitted, the interactive wizard runs instead.",
)
@click.option("--wizard", "-w", is_flag=True, help="Force the interactive configuration wizard.")
@click.option("--default", "-d", "use_default", is_flag=True, help="Accept all defaults (skip the wizard, no prompts).")
@click.option(
    "--service",
    "-s",
    "services",
    multiple=True,
    help="Enable exactly these services (repeatable). Defaults to the template's selection.",
)
@click.option(
    "--coord-server",
    default=None,
    help="External coordination (auth) server whose JWKS the services trust.",
)
@click.option(
    "--rekuest-server",
    default=None,
    help="Rekuest (provenance) server host ('local' runs rekuest as a core dependency).",
)
@click.option("--port", type=int, default=None, help="Exposed HTTP port.")
@click.option("--ssl-port", type=int, default=None, help="Exposed HTTPS port.")
@click.option("--backend", default="docker", help="Deployment backend (docker, podman, kubernetes).")
@click.pass_context
def init(ctx, path, template, wizard, use_default, services, coord_server, rekuest_server, port, ssl_port, backend) -> None:
    """Initialize a hub configuration (services, no local coordinator).

    A hub never asks about organizations or users -- only about the local
    servers/services. Explicit options override the wizard/template defaults.
    """
    from arkitekt_next.server.deployments import DEPLOYMENTS

    spec = DEPLOYMENTS["hub"]
    console = get_console(ctx)
    target = resolve_path(ctx, path)

    config = select_config(spec, console, wizard=wizard, template=template, use_default=use_default)

    # Explicit CLI options override wizard/template defaults (only when provided).
    if services:
        set_enabled_services(config, services)
    if coord_server is not None:
        config.coord_server = coord_server
    if rekuest_server is not None:
        config.rekuest_server = rekuest_server
        config.rekuest.enabled = rekuest_server == "local"
    if port is not None:
        config.gateway.exposed_http_port = port
    if ssl_port is not None:
        config.gateway.exposed_https_port = ssl_port

    console.print(
        f"Creating [bold]hub[/bold] ({template or 'wizard'}) trusting coordinator "
        f"[cyan]{config.coord_server}[/cyan] at [cyan]{target}[/cyan]..."
    )
    finalize(ctx, target, config, spec, template=template, backend=backend)


hub.add_command(
    make_up_command("hub", help="Compose the hub (services + auth wiring) and run `docker compose up`."),
    "up",
)
hub.add_command(connect, "connect")
