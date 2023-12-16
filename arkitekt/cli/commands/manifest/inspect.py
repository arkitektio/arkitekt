import rich_click as click
from rich.table import Table
from rich.panel import Panel
from rich.console import Group
from arkitekt.cli.vars import get_manifest, get_console


@click.command()
@click.pass_context
def inspect(ctx) -> None:
    """Inspect the [i]current[/i] manifest of this app

    The manifest is used to describe the app and its rights (scopes) and requirements, to be run on the platform.
    This manifest is used to authenticate the app with the platform establishing its scopes and requirements.


    """
    manifest = get_manifest(ctx)

    table = Table.grid()
    table.add_column()
    table.add_column()
    table.add_row("Identifier", manifest.identifier)
    table.add_row("Version", manifest.version)
    table.add_row("Author", manifest.author)
    table.add_row("Logo", manifest.logo or "-")
    table.add_row("Entrypoint", manifest.entrypoint)
    table.add_row("Scopes", ", ".join(manifest.scopes) if manifest.scopes else "-")
    table.add_row(
        "Requirements",
        ", ".join(manifest.requirements) if manifest.requirements else "-",
    )
    table.add_row("Created at", str(manifest.created_at.strftime("%Y/%m/%d %H:%M")))

    panel = Panel(
        Group("[bold green]Manifest[/]", table),
        title_align="center",
        border_style="green",
        style="white",
    )

    get_console(ctx).print(panel)
