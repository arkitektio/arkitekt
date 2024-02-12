import rich_click as click
from click import Context
from dokker.projects.contrib.konstruktor import KonstruktorProject, RemoteRepo
import asyncio
from typing import Optional
import os
from arkitekt.cli.vars import get_console
from arkitekt.deployed import deployment
DEFAULT_REPO_URL = "https://arkitekt.live/repo.json"


def create_nested_dict_from_dict(paths_values_dict):
    final_dict = {}
    for path, value in paths_values_dict.items():
        keys = path.split(".")
        current_level = final_dict
        for key in keys[:-1]:
            if key not in current_level:
                current_level[key] = {}
            current_level = current_level[key]
        current_level[keys[-1]] = value
    return final_dict


@click.command()
@click.option(
    "--name",
    help="The name of the deployment",
    default="default",
    required=True,
)
@click.option(
    "--setup",
    "-s",
    "setup",
    help="Additional setup variables",
    type=(str, str),
    multiple=True,
)
@click.option(
    "--overwrite",
    "-o",
    "overwrite",
    help="Overwrite the existing deployment",
    is_flag=True,
)
@click.pass_context
def init(
    ctx: Context,
    setup: Optional[list] = None,
    name: Optional[str] = None,
    overwrite: Optional[bool] = False,
) -> None:
    """
    Initializes a new server

    """

    extra_content = dict(setup or [])

    console = get_console(ctx)

    defaults = create_nested_dict_from_dict(extra_content)
    with deployment(name, ) as d:

        with d.watch_logs("lok"):
            d.check_health()


        if overwrite:
            console.print("Removing old deployment")
            d.remove()

        d.initialize(**defaults)

