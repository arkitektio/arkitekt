import rich_click as click
from click import Context
from dokker.projects.contrib.konstruktor import KonstruktorProject
import asyncio
from typing import Optional, Any
import os

DEFAULT_REPO_URL = (
    "https://raw.githubusercontent.com/jhnnsrs/konstruktor/master/repo/channels.json"
)


@click.command()
@click.option("--channel", help="The channel to use", default="paper")
@click.option("--name", help="The name of the deployment", default=None, required=False)
@click.option("--overwrite", help="The repo to use", default=False, is_flag=True)
@click.option("--repo-url", help="The repo to use", default=DEFAULT_REPO_URL)
@click.option(
    "--setup",
    "-s",
    "setup",
    help="Key Value pairs for the setup",
    type=(str, str),
    multiple=True,
)
@click.pass_context
def init(
    ctx: Context,
    channel: str,
    repo_url: str,
    overwrite: bool = False,
    setup: Optional[list] = None,
    name: Optional[str] = None,
) -> None:
    """
    Initializes a new deployment from a konstruktor template.
    this will create a new folder in the .arkitekt/deployments folder
    with the name of the deployment and the docker-compose.yml file

    """

    extra_content = dict(setup or [])

    project = KonstruktorProject(
        channel=channel,
        repo_url=repo_url,
        overwrite_if_exists=overwrite,
        name=name,
        extra_context=extra_content,
        base_dir=os.path.join(os.getcwd(), ".arkitekt", "deployments"),
    )

    asyncio.run(project.ainititialize())
