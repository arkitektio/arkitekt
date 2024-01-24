import rich_click as click
from click import Context
from dokker.projects.contrib.konstruktor import KonstruktorProject, RemoteRepo
import asyncio
from typing import Optional
import os
from arkitekt.cli.vars import get_console

DEFAULT_REPO_URL = "https://arkitekt.live/repo.json"


@click.command()
@click.option(
    "--repo-url",
    help="The repo to use",
    default=DEFAULT_REPO_URL,
    prompt="What repo do you want to use?",
)
@click.option(
    "--channel",
    help="The channel to use",
    default="beta",
    prompt="What channel do you want to use?",
)
@click.option(
    "--name",
    help="The name of the deployment",
    default=None,
    required=False,
)
@click.option(
    "--overwrite",
    help="Should we overwrite the old deployment?",
    default=False,
    is_flag=True,
)
@click.option(
    "--setup",
    "-s",
    "setup",
    help="Additional setup variables",
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
    Initializes a new server

    """

    extra_content = dict(setup or [])

    project = KonstruktorProject(
        channel=channel,
        repo=RemoteRepo(url=repo_url),
        reinit_if_exists=overwrite,
        name=name,
        extra_context=extra_content,
    )

    try:
        asyncio.run(project.ainititialize())
        get_console(ctx).print("Done :)")
    except Exception as e:
        get_console(ctx).print_exception()
        raise click.ClickException("Failed to initialize project") from e
