import rich_click as click

from arkitekt_next.cli.docs import COORD_DOCS, help_epilog
from arkitekt_next.cli.vars import get_console
from arkitekt_next.cli.commands._server_common import (
    finalize,
    make_up_command,
    require_server_deps,
    resolve_path,
    select_config,
)


@click.group(epilog=help_epilog(COORD_DOCS))
@click.pass_context
def coord(ctx) -> None:
    """Run a coordinator: the standalone Lok auth server + Kontrol frontend.

    A coordinator issues identity (OIDC/JWKS via Lok) and serves the Kontrol web
    frontend that clients and hubs authenticate against. It runs no data/compute
    services and no deployer -- point one or more `hub`s at it via their
    `--coord-server`.
    """
    require_server_deps()


@coord.command()
@click.argument("path", required=False)
@click.option(
    "--template",
    "-t",
    default=None,
    help="Config template (stable, dev, default, minimal). If omitted, the interactive wizard runs and asks whether to set up organizations.",
)
@click.option("--wizard", "-w", is_flag=True, help="Force the interactive configuration wizard.")
@click.option("--default", "-d", "use_default", is_flag=True, help="Accept all defaults (skip the wizard, no prompts).")
@click.option("--port", type=int, default=None, help="Exposed HTTP port.")
@click.option("--ssl-port", type=int, default=None, help="Exposed HTTPS port.")
@click.option("--backend", default="docker", help="Deployment backend (docker, podman, kubernetes).")
@click.pass_context
def init(ctx, path, template, wizard, use_default, port, ssl_port, backend) -> None:
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


coord.add_command(
    make_up_command("coord", help="Compose the coordinator (Lok + auth wiring) and run `docker compose up`."),
    "up",
)
