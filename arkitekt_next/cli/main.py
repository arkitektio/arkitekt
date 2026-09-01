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
    CALL_DOCS,
    GEN_DOCS,
    INIT_DOCS,
    INSPECT_DOCS,
    MANIFEST_DOCS,
    MESH_DOCS,
    PLUGIN_DOCS,
    RUN_DOCS,
    SELF_DOCS,
    help_epilog,
)
from arkitekt_next.cli.commands.app.call.main import call
from arkitekt_next.cli.commands.app.gen.main import gen
from arkitekt_next.cli.commands.app.init.main import init_command
from arkitekt_next.cli.commands.app.inspect.main import inspect
from arkitekt_next.cli.commands.app.manifest.main import manifest
from arkitekt_next.cli.commands.app.run.main import run
from arkitekt_next.cli.commands.mesh.main import mesh
from arkitekt_next.cli.commands.self.main import self_group
from arkitekt_next.cli.commands.plugin.main import plugin

# Mount every group onto the Typer root, then build the public click entry point
# (project.scripts -> arkitekt_next.cli.main:cli). The root callback in cli/app.py seeds
# ctx.obj (and, for the app-project commands, the manifest), which propagates to every
# subcommand. Per-group `epilog` re-adds the hosted docs link to each `--help`. Server
# construction and deployment live in konstruktor
# (https://github.com/arkitektio/konstruktor), not here.

# `init` is a single leaf command (not a group), so register it directly rather than
# as a sub-Typer (add_typer would turn its positional PATH arg into a subcommand slot).
cli_app.command("init", epilog=help_epilog(INIT_DOCS))(init_command)
cli_app.add_typer(run, name="run", epilog=help_epilog(RUN_DOCS))
cli_app.add_typer(gen, name="gen", epilog=help_epilog(GEN_DOCS))
cli_app.add_typer(manifest, name="manifest", epilog=help_epilog(MANIFEST_DOCS))
cli_app.add_typer(inspect, name="inspect", epilog=help_epilog(INSPECT_DOCS))
cli_app.add_typer(call, name="call", epilog=help_epilog(CALL_DOCS))
cli_app.add_typer(mesh, name="mesh", epilog=help_epilog(MESH_DOCS))
cli_app.add_typer(self_group, name="self", epilog=help_epilog(SELF_DOCS))
cli_app.add_typer(plugin, name="plugin", epilog=help_epilog(PLUGIN_DOCS))

cli = typer.main.get_command(cli_app)

if __name__ == "__main__":
    cli()
