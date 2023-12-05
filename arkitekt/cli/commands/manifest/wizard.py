from enum import Enum
import os
import rich_click as click
from arkitekt.cli.types import Requirement, Framework
from rich.table import Table
from rich.panel import Panel
from rich.console import Console, Group
from arkitekt.cli.vars import get_manifest, get_console


def check_dl_frameworks():
    import site
    import sys

    site_packages = site.getsitepackages()
    site_packages.append(sys.prefix)

    frameworks = {
        "tensorflow": Framework.TENSORFLOW,
        "torch": Framework.PYTORCH,
        "torchvision": Framework.PYTORCH,
        "tensorflow-gpu": Framework.TENSORFLOW,
        "torch-gpu": Framework.PYTORCH,
        "torchvision-gpu": Framework.PYTORCH,
    }

    included_frameworks = set()

    for key, value in frameworks.items():
        for site_package in site_packages:
            if os.path.exists(os.path.join(site_package, key)):
                included_frameworks.add(value)

    return included_frameworks


def inspect_requirements(automatic=False):
    """Inspect the requirements and


    return a list of requirements and reasons.

    Parameters
    ----------
    automatic : bool, optional
        Should we automically add all of the requirements, by default False

    Returns
    -------
    _type_
        _description_
    """
    requirements = []
    reasons = []
    frameworks = check_dl_frameworks()
    if frameworks:
        requirements.append(Requirement.GPU)
        reasons.append(
            "Deep learning framework detected ('{}')".format(", ".join(frameworks))
        )

    return requirements, reasons


@click.command()
@click.pass_context
def wizard(ctx) -> None:
    """Inspect the current project

    And ask the user for the required information to create a manifest.




    """
    console = get_console(ctx)
    requirements, reasons = inspect_requirements()

    table = Table.grid()
    table.add_column()
    table.add_column()

    for item in zip(requirements, reasons):
        table.add_row(str(item[0]), item[1])

    panel = Panel(
        Group("[bold green]Manifest[/]", table),
        title_align="center",
        border_style="green",
        style="white",
    )

    console.print(panel)
