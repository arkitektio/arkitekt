from typing import Annotated, Optional

import typer

from arkitekt_next.cli.vars import get_console
from arkitekt_next.cli.commands._server_common import (
    finalize,
    make_up_command,
    require_server_deps,
    resolve_path,
    select_config,
)

coord = typer.Typer(
    no_args_is_help=True,
    help="""Run a coordinator: the standalone Lok auth server + Kontrol frontend.

    A coordinator issues identity (OIDC/JWKS via Lok) and serves the Kontrol web
    frontend that clients and hubs authenticate against. It runs no data/compute
    services and no deployer -- point one or more `hub`s at it via their
    `--coord-server`.
    """,
)


@coord.callback()
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
            help="Config template (stable, dev, default, minimal). If omitted, the interactive wizard runs and asks whether to set up organizations.",
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
    port: Annotated[Optional[int], typer.Option("--port", help="Exposed HTTP port.")] = None,
    ssl_port: Annotated[Optional[int], typer.Option("--ssl-port", help="Exposed HTTPS port.")] = None,
    backend: Annotated[
        str,
        typer.Option("--backend", help="Deployment backend (docker, podman, kubernetes)."),
    ] = "docker",
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

    config = select_config(spec, console, wizard=wizard, template=template, use_default=use_default)

    if port is not None:
        config.gateway.exposed_http_port = port
    if ssl_port is not None:
        config.gateway.exposed_https_port = ssl_port

    console.print(
        f"Creating [bold]coordinator[/bold] ({template or 'wizard'}) with Lok + Kontrol "
        f"at [cyan]{target}[/cyan]..."
    )
    finalize(ctx, target, config, spec, template=template, backend=backend)


coord.command("init")(init)
coord.command("up")(make_up_command("coord"))
