import rich_click as click

from arkitekt_next.cli.docs import ENGINE_DOCS, help_epilog
from arkitekt_next.cli.vars import get_console
from arkitekt_next.cli.commands._server_common import (
    finalize,
    make_up_command,
    require_server_deps,
    resolve_path,
)


@click.group(epilog=help_epilog(ENGINE_DOCS))
@click.pass_context
def engine(ctx) -> None:
    """Run a standalone engine: a deployer in its own docker-compose.

    An engine is just a deployer running on its own. It connects to an existing
    Arkitekt deployment (a hub, coord or hubinator) and orchestrates app
    containers on its behalf. Only the `hubinator` bundles a deployer inline;
    everywhere else you run an engine. Use `engine init` then `engine up`.
    """
    require_server_deps()


@engine.command()
@click.argument("path", required=False)
@click.option("--url", default=None, help="Gateway URL of the Arkitekt deployment to connect to.")
@click.option("--redeem-token", default=None, help="Redeem token issued by the target deployment.")
@click.option("--network", default=None, help="Docker network to join (the target deployment's internal network).")
@click.option("--organization", default=None, help="Organization the deployer acts on behalf of.")
@click.option("--instance-id", default=None, help="Instance ID for the deployer.")
@click.option("--backend", default="docker", help="Deployment backend (docker, podman, kubernetes).")
@click.pass_context
def init(ctx, path, url, redeem_token, network, organization, instance_id, backend) -> None:
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


engine.add_command(
    make_up_command("engine", help="Compose the engine (deployer) and run `docker compose up`."),
    "up",
)
