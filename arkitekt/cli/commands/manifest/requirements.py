import rich_click as click
from arkitekt.cli.vars import get_manifest, get_console
from arkitekt.cli.constants import *
from rich.table import Table
from rich.panel import Panel
from rich.console import Group
from arkitekt.cli.vars import *
from arkitekt.cli.constants import *
from arkitekt.cli.io import write_manifest


@click.group("requirements")
@click.pass_context
def requirements_group(ctx):
    """Inspect, add and remove requirements to this arkitekt app

    Requirements are used to hint the user to have specific hardware or software installed, when
    using your application. It is also used to inform the platform about the requirements of your app,
    when installing it in its plugin sandbox. for more information, please visit the [link=https://jhnnsrs.github.io/doks]https://jhnnsrs.github.io/doks[/link]

    """


@requirements_group.command("add")
@click.argument(
    "REQUIREMENTS",
    nargs=-1,
    type=click.Choice(compile_requirements()),
)
@click.pass_context
def add_requirement(ctx, requirements):
    """Add requiremenets

    Requirements are used to hint the user to have specific hardware or software installed, when
    using your application. It is also used to inform the platform about the requirements of your app,
    when installing it in its plugin sandbox. for more information, please visit the [link=https://jhnnsrs.github.io/doks]https://jhnnsrs.github.io/doks[/link]

    """
    if not requirements:
        raise click.ClickException("Please provide at least one requirement")

    manifest = get_manifest(ctx)
    console = get_console(ctx)

    if requirements:
        manifest.requirements = set(list(requirements) + manifest.requirements)
        write_manifest(manifest)
        console.print(f"Requirements Updated to {manifest.requirements}")


@requirements_group.command("remove")
@click.argument(
    "REQUIREMENTS",
    nargs=-1,
    type=click.Choice(compile_requirements()),
)
@click.pass_context
def remove_requirements(ctx, requirements):
    """Remove requirements

    Requirements are used to hint the user to have specific hardware or software installed, when
    using your application. It is also used to inform the platform about the requirements of your app,
    when installing it in its plugin sandbox. for more information, please visit the [link=https://jhnnsrs.github.io/doks]https://jhnnsrs.github.io/doks[/link]


    """
    if not requirements:
        raise click.ClickException("Please provide at least one requirement to remove")

    manifest = get_manifest(ctx)
    console = get_console(ctx)

    if requirements:
        manifest.requirements = set(manifest.requirements) - set(requirements)
        write_manifest(manifest)
        console.print(f"Requirements Updated to {manifest.requirements}")


@requirements_group.command("list")
@click.pass_context
def list_requirements(ctx):
    """Lists the [i]current[/] requirements

    Requirements are used to hint the user to have specific hardware or software installed, when
    using your application. It is also used to inform the platform about the requirements of your app,
    when installing it in its plugin sandbox. for more information, please visit the [link=https://jhnnsrs.github.io/doks]https://jhnnsrs.github.io/doks[/link]

    """

    manifest = get_manifest(ctx)
    console = get_console(ctx)

    table = Table(
        title="[green bold ]Requirements[/]",
        title_justify="left",
        title_style="green bold",
    )
    table.add_column("Requirement")
    table.add_column("Description")

    for scope in manifest.requirements:
        table.add_row(scope, "TODO")

    panel = Panel(
        table,
        title_align="center",
        border_style="green",
        style="white",
    )

    console.print(panel)


@requirements_group.command("available")
@click.pass_context
def list_available_requirements(ctx):
    """Lists the [i]available[/] requirements

    Requirements are used to hint the user to have specific hardware or software installed, when
    using your application. It is also used to inform the platform about the requirements of your app,
    when installing it in its plugin sandbox. for more information, please visit the [link=https://jhnnsrs.github.io/doks]https://jhnnsrs.github.io/doks[/link]

    """

    console = get_console(ctx)

    table = Table.grid()
    table.add_column("Scope")
    table.add_column("Description")
    for scope in compile_requirements():
        table.add_row(scope, "TODO")

    panel = Panel(
        Group("[bold green]Available Scopes[/]", table),
        title_align="center",
        border_style="green",
        style="white",
    )

    console.print(panel)
