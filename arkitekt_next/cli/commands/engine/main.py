from typing import Annotated, Optional

import typer

from arkitekt_next.cli.vars import get_console
from arkitekt_next.cli.commands._server_common import (
    finalize,
    make_up_command,
    require_server_deps,
    resolve_path,
)

engine = typer.Typer(
    no_args_is_help=True,
    help="""Run a standalone engine: a deployer in its own docker-compose.

    An engine is just a deployer running on its own. It connects to an existing
    Arkitekt deployment (a hub, coord or hubinator) and orchestrates app
    containers on its behalf. Only the `hubinator` bundles a deployer inline;
    everywhere else you run an engine. Use `engine init` then `engine up`.
    """,
)


@engine.callback()
def _root(ctx: typer.Context) -> None:
    require_server_deps()


def init(
    ctx: typer.Context,
    path: Annotated[Optional[str], typer.Argument()] = None,
    url: Annotated[
        Optional[str],
        typer.Option("--url", help="Gateway URL of the Arkitekt deployment to connect to."),
    ] = None,
    redeem_token: Annotated[
        Optional[str],
        typer.Option("--redeem-token", help="Redeem token issued by the target deployment."),
    ] = None,
    network: Annotated[
        Optional[str],
        typer.Option("--network", help="Docker network to join (the target deployment's internal network)."),
    ] = None,
    organization: Annotated[
        Optional[str],
        typer.Option("--organization", help="Organization the deployer acts on behalf of."),
    ] = None,
    instance_id: Annotated[
        Optional[str],
        typer.Option("--instance-id", help="Instance ID for the deployer."),
    ] = None,
    backend: Annotated[
        str,
        typer.Option("--backend", help="Deployment backend (docker, podman, kubernetes)."),
    ] = "docker",
) -> None:
    """Initialize a standalone engine (deployer) configuration."""
    from arkitekt_next.server.config import EngineConfig
    from arkitekt_next.server.deployments import DEPLOYMENTS

    spec = DEPLOYMENTS["engine"]
    console = get_console(ctx)
    target = resolve_path(ctx, path)

    # Engine has no wizard or templates -- build the default config and apply options.
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


engine.command("init")(init)
engine.command("up")(make_up_command("engine"))
