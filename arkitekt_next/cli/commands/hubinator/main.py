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

hubinator = typer.Typer(
    no_args_is_help=True,
    help="""Run the full stack: a hub AND a local coordinator in one deployment.

    A hubinator is a self-contained Arkitekt instance -- the data/compute
    services plus a local Lok coordinator (with Kontrol frontend) and, optionally,
    a deployer. This is the all-in-one deployment the standalone arkitekt-server
    tool produced by default. Use `hubinator init` then `hubinator up`.
    """,
)


@hubinator.callback()
def _root(ctx: typer.Context) -> None:
    require_server_deps()


def init(
    ctx: typer.Context,
    path: Annotated[Optional[str], typer.Argument()] = None,
    template: Annotated[
        str,
        typer.Option("--template", "-t", help="Config template (stable, dev, default, minimal)."),
    ] = "default",
    wizard: Annotated[
        bool,
        typer.Option("--wizard", "-w", help="Run the interactive configuration wizard."),
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
    rekuest_server: Annotated[
        str,
        typer.Option(
            "--rekuest-server",
            help="Rekuest (provenance) server host ('local' runs rekuest as a core dependency).",
        ),
    ] = "local",
    port: Annotated[Optional[int], typer.Option("--port", help="Exposed HTTP port.")] = None,
    ssl_port: Annotated[Optional[int], typer.Option("--ssl-port", help="Exposed HTTPS port.")] = None,
    backend: Annotated[
        str,
        typer.Option("--backend", help="Deployment backend (docker, podman, kubernetes)."),
    ] = "docker",
) -> None:
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


hubinator.command("init")(init)
hubinator.command("up")(make_up_command("hubinator"))
