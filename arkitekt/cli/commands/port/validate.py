from arkitekt.cli.types import Flavour
import rich_click as click
from click import Context
from rich import get_console
from arkitekt.utils import create_arkitekt_folder
import yaml


try:
    pass
except ImportError as e:
    raise ImportError("Please install rekuest to use this feature") from e

import os


@click.command()
@click.option("--flavour", "-f", help="The flavour to use", default=None)
@click.option(
    "--description",
    "-d",
    help="The description for this flavour to use",
    default="This is a vanilla flavour",
)
@click.option(
    "--overwrite",
    "-o",
    help="Should we overwrite the existing Dockerfile?",
    is_flag=True,
    default=False,
)
@click.pass_context
def validate(ctx: Context, description: str, overwrite: bool, flavour: str) -> None:
    """Runs the port wizard to generate a dockerfile to be used with port"""

    arkitekt_folder = create_arkitekt_folder()

    flavours_folder = os.path.join(arkitekt_folder, "flavours")

    if not os.path.exists(flavours_folder):
        raise click.ClickException(
            "We could not find the flavours folder. Please run arkitekt port init first"
        )

    for dir_name in os.listdir(flavours_folder):
        dir = os.path.join(flavours_folder, dir_name)
        if os.path.isdir(dir):
            if flavour is not None and flavour != dir_name:
                continue

            if os.path.exists(os.path.join(dir, "config.yaml")):
                with open(os.path.join(dir, "config.yaml")) as f:
                    valued = yaml.load(f, Loader=yaml.SafeLoader)
                try:
                    flavour = Flavour(**valued)

                except Exception as e:
                    get_console().print_exception()
                    raise click.ClickException(f"Flavour {dir_name} is invalid") from e

                try:
                    flavour.check_relative_paths(dir)
                except Exception as e:
                    raise click.ClickException(
                        f"Relative Paths in Flavour {dir_name} are invalid. {e}"
                    ) from e

            else:
                raise click.ClickException(
                    f"Flavour {dir_name} is invalid. No config.yaml file found"
                )

        else:
            print(
                f"Found file {dir_name} in flavours folder. Not a valid flavour. Ignoring"
            )

    click.echo("Ice Ice Baby! All flavours are valid")
