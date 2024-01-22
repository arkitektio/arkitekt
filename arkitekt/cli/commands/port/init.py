from arkitekt.cli.constants import compile_dockerfiles
from arkitekt.cli.types import Flavour
from arkitekt.cli.utils import build_relative_dir
import rich_click as click
from click import Context
from rich import get_console
from arkitekt.utils import create_arkitekt_folder
import yaml
from rich.panel import Panel

try:
    pass
except ImportError as e:
    raise ImportError("Please install rekuest to use this feature") from e

import os


@click.command()
@click.option("--flavour", "-f", help="The flavour to use", default="vanilla")
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
@click.option(
    "--template",
    "-t",
    help="The dockerfile template to use",
    default="vanilla",
    type=click.Choice(compile_dockerfiles()),
)
@click.pass_context
def init(
    ctx: Context, description: str, overwrite: bool, flavour: str, template: str
) -> None:
    """Runs the port wizard to generate a dockerfile to be used with port"""

    arkitekt_folder = create_arkitekt_folder()

    flavour_folder = os.path.join(arkitekt_folder, "flavours", flavour)
    if os.path.exists(flavour_folder) and not overwrite:
        raise click.ClickException(
            f"The flavour {flavour} does already exist. Please initialize a different flavour or use the --overwrite flag"
        )
    else:
        os.makedirs(flavour_folder, exist_ok=True)

    config_file = os.path.join(flavour_folder, "config.yaml")
    dockerfile = os.path.join(flavour_folder, "Dockerfile")

    fl = Flavour(
        selectors=[],
        description=description,
        dockerfile="Dockerfile",
    )

    with open(config_file, "w") as file:
        yaml.dump(fl.dict(), file)

    with open(build_relative_dir("dockerfiles", f"{template}.dockerfile"), "r") as f:
        dockerfile_content = f.read()

    with open(dockerfile, "w") as f:
        f.write(dockerfile_content)

    panel = Panel(
        title=f"Created new flavour [bold]{flavour}[/bold]\n",
        renderable="You can now edit the Dockerfile and add selectors to the config.yaml file\n"
        + "To learn more about selectors and how flavours work, please visit [link=https://arkitekt.live]https://arkitekt.live[/link]",
        style="green",
    )

    get_console().print(panel)
