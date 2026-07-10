from typing import Annotated, List, Optional

import typer

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

hub = typer.Typer(
    no_args_is_help=True,
    help="""Run a hub: a stack of Arkitekt services WITHOUT a local coordinator.

    A hub bundles the data/compute services (rekuest, mikro, fluss, ...) and
    trusts an external coordination (auth) server for identity. It manages no
    organizations or users, and comes with no deployer. Use `hub init` to write
    the config, `hub up` to compose and start the stack, and `hub connect` to
    register the hub's services with an organization. If you also want to run the
    coordinator locally, use `hubinator` instead.
    """,
)


@hub.callback()
def _root(ctx: typer.Context) -> None:
    require_server_deps()


def init(
    ctx: typer.Context,
    path: Annotated[Optional[str], typer.Argument()] = None,
    template: Annotated[
        Optional[str],
        typer.Option(
            "--template",
            "-t",
            help="Config template (stable, dev, default, minimal). If omitted, the interactive wizard runs instead.",
        ),
    ] = None,
    wizard: Annotated[
        bool,
        typer.Option("--wizard", "-w", help="Force the interactive configuration wizard."),
    ] = False,
    use_default: Annotated[
        bool,
        typer.Option("--default", "-d", help="Accept all defaults (skip the wizard, no prompts)."),
    ] = False,
    services: Annotated[
        List[str],
        typer.Option(
            "--service",
            "-s",
            help="Enable exactly these services (repeatable). Defaults to the template's selection.",
        ),
    ] = [],
    coord_server: Annotated[
        Optional[str],
        typer.Option(
            "--coord-server",
            help="External coordination (auth) server whose JWKS the services trust.",
        ),
    ] = None,
    rekuest_server: Annotated[
        Optional[str],
        typer.Option(
            "--rekuest-server",
            help="Rekuest (provenance) server host ('local' runs rekuest as a core dependency).",
        ),
    ] = None,
    port: Annotated[Optional[int], typer.Option("--port", help="Exposed HTTP port.")] = None,
    ssl_port: Annotated[Optional[int], typer.Option("--ssl-port", help="Exposed HTTPS port.")] = None,
    backend: Annotated[
        str,
        typer.Option("--backend", help="Deployment backend (docker, podman, kubernetes)."),
    ] = "docker",
) -> None:
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


hub.command("init")(init)
hub.command("up")(make_up_command("hub"))
hub.command("connect")(connect)
