import sys

try:
    import typer
except ImportError:
    print(
        "ArkitektNext CLI is not installed, please install it first. By installing the cli, e.g with `pip install arkitekt_next[cli]`, you can use the `arkitekt_next` command."
    )
    sys.exit(1)

from arkitekt_next.cli.app import cli_app
from arkitekt_next.cli.docs import (
    COORD_DOCS,
    ENGINE_DOCS,
    HUB_DOCS,
    HUBINATOR_DOCS,
    MESH_DOCS,
    PLUGIN_DOCS,
    SELF_DOCS,
    help_epilog,
)
from arkitekt_next.cli.commands.app.main import app
from arkitekt_next.cli.commands.hub.main import hub
from arkitekt_next.cli.commands.coord.main import coord
from arkitekt_next.cli.commands.mesh.main import mesh
from arkitekt_next.cli.commands.hubinator.main import hubinator
from arkitekt_next.cli.commands.engine.main import engine
from arkitekt_next.cli.commands.self.main import self_group
from arkitekt_next.cli.commands.plugin.main import plugin

# Mount every group onto the Typer root, then build the public click entry point
# (project.scripts -> arkitekt_next.cli.main:cli). The root callback in cli/app.py seeds
# ctx.obj, which propagates to every subcommand. Per-group `epilog` re-adds the hosted
# docs link to each `--help` (the `app` group sets its own; its subgroups get theirs in
# app/main.py).
cli_app.add_typer(app, name="app")
cli_app.add_typer(hub, name="hub", epilog=help_epilog(HUB_DOCS))
cli_app.add_typer(coord, name="coord", epilog=help_epilog(COORD_DOCS))
cli_app.add_typer(mesh, name="mesh", epilog=help_epilog(MESH_DOCS))
cli_app.add_typer(hubinator, name="hubinator", epilog=help_epilog(HUBINATOR_DOCS))
cli_app.add_typer(engine, name="engine", epilog=help_epilog(ENGINE_DOCS))
cli_app.add_typer(self_group, name="self", epilog=help_epilog(SELF_DOCS))
cli_app.add_typer(plugin, name="plugin", epilog=help_epilog(PLUGIN_DOCS))

cli = typer.main.get_command(cli_app)

if __name__ == "__main__":
    cli()
