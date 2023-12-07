import rich_click as click
from rich.table import Table
from rich.panel import Panel
from rich.console import Group
from arkitekt.cli.vars import *
from arkitekt.cli.constants import *
from arkitekt.cli.io import write_manifest


@click.group("scopes")
@click.pass_context
def scopes_group(ctx):
    """Inspect, add and remove scopes to this arkitekt app

    Scopes are rights that are granted to any arkitekt application, and correspond
    to rights that enable feature when interacting with the platform. These scopes
    provide another element of access control to the arkitekt platform, and describe
    on top of the users rights, what the application is allowed to do.

    For more information, please visit the [link=https://jhnnsrs.github.io/doks]https://jhnnsrs.github.io/doks[/link]


    """
    pass


@scopes_group.command("add")
@click.argument(
    "SCOPE",
    nargs=-1,
    type=click.Choice(compile_scopes()),
)
@click.pass_context
def add_scopes(ctx, scope):
    """ "Acd scopes

    Scopes are rights that are granted to any arkitekt application, and correspond
    to rights that enable feature when interacting with the platform. These scopes
    provide another element of access control to the arkitekt platform, and describe
    on top of the users rights, what the application is allowed to do.

    For more information, please visit the [link=https://jhnnsrs.github.io/doks]https://jhnnsrs.github.io/doks[/link]


    """
    if not scope:
        raise click.ClickException("Please provide at least one scope")

    manifest = get_manifest(ctx)
    console = get_console(ctx)

    if scope:
        manifest.scopes = set(list(scope) + manifest.scopes)
        write_manifest(manifest)
        console.print(f"Scopes Updated to {manifest.scopes}")


@scopes_group.command("remove")
@click.argument(
    "SCOPE",
    nargs=-1,
    type=click.Choice(compile_scopes()),
)
@click.pass_context
def remove_scopes(ctx, scope):
    """Remove scopes

    Scopes are rights that are granted to any arkitekt application, and correspond
    to rights that enable feature when interacting with the platform. These scopes
    provide another element of access control to the arkitekt platform, and describe
    on top of the users rights, what the application is allowed to do.

    For more information, please visit the [link=https://jhnnsrs.github.io/doks]https://jhnnsrs.github.io/doks[/link]


    """
    if not scope:
        raise click.ClickException("Please provide at least one scope to remove")

    manifest = get_manifest(ctx)
    console = get_console(ctx)

    if scope:
        manifest.scopes = set(manifest.scopes) - set(scope)
        write_manifest(manifest)
        console.print(f"Scopes Updated to {manifest.scopes}")


@scopes_group.command("list")
@click.pass_context
def list_scopes(ctx):
    """List all the [i] currently [/] active scopes

    Scopes are rights that are granted to any arkitekt application, and correspond
    to rights that enable feature when interacting with the platform. These scopes
    provide another element of access control to the arkitekt platform, and describe
    on top of the users rights, what the application is allowed to do.

    For more information, please visit the [link=https://jhnnsrs.github.io/doks]https://jhnnsrs.github.io/doks[/link]


    """

    manifest = get_manifest(ctx)
    console = get_console(ctx)

    table = Table.grid()
    table.padding = (0, 1)
    table.add_column("Scope")
    table.add_column("Description")
    for scope in manifest.scopes:
        table.add_row(scope, "TODO: This should be a description")

    panel = Panel(
        Group("[bold green]Demanded Scopes[/]", table),
        title_align="center",
        border_style="green",
        style="white",
    )

    console.print(panel)


@scopes_group.command("available")
@click.pass_context
def list_available(ctx):
    """List all the [i] available [/]  scopes

    Scopes are rights that are granted to any arkitekt application, and correspond
    to rights that enable feature when interacting with the platform. These scopes
    provide another element of access control to the arkitekt platform, and describe
    on top of the users rights, what the application is allowed to do.

    For more information, please visit the [link=https://jhnnsrs.github.io/doks]https://jhnnsrs.github.io/doks[/link]


    """

    console = get_console(ctx)

    table = Table.grid()
    table.padding = (0, 1)
    table.add_column("Scope")
    table.add_column("Description")
    for scope in compile_scopes():
        table.add_row(scope, "TODO")

    panel = Panel(
        Group("[bold green]Available Scopes[/]", table),
        title_align="center",
        border_style="green",
        style="white",
    )

    console.print(panel)
