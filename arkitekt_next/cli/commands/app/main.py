import typer

from arkitekt_next.cli.docs import (
    APP_DOCS,
    CALL_DOCS,
    GEN_DOCS,
    INIT_DOCS,
    INSPECT_DOCS,
    MANIFEST_DOCS,
    RUN_DOCS,
    help_epilog,
)
from arkitekt_next.cli.vars import set_manifest, get_work_dir
from arkitekt_next.cli.io import load_manifest
from arkitekt_next.utils import create_arkitekt_next_folder

from arkitekt_next.cli.commands.app.run.main import run
from arkitekt_next.cli.commands.app.gen.main import gen
from arkitekt_next.cli.commands.app.init.main import init_command
from arkitekt_next.cli.commands.app.manifest.main import manifest
from arkitekt_next.cli.commands.app.inspect.main import inspect
from arkitekt_next.cli.commands.app.call.main import call

app = typer.Typer(
    no_args_is_help=True,
    help="""Build, run and deploy ArkitektNext apps from your Python code.

    These are the client-side SDK commands: scaffold a new app (`init`), run it
    locally (`run`), generate typed clients (`gen`), manage its manifest and
    call functions. Every command here operates on the app in the current
    working directory (see `--work-dir`). To package the app as a deployable
    plugin, see the top-level `plugin` group.
    """,
    epilog=help_epilog(APP_DOCS),
)


@app.callback()
def _root(ctx: typer.Context) -> None:
    # The app commands operate on a scaffolded project (a manifest inside the
    # `.arkitekt_next` folder). Every subcommand except `init` (which creates that
    # project) needs the folder to exist and the manifest loaded into context.
    if ctx.invoked_subcommand != "init":
        work_dir = get_work_dir(ctx)
        create_arkitekt_next_folder(base_dir=work_dir)

        manifest = load_manifest(base_dir=work_dir)
        if manifest:
            set_manifest(ctx, manifest)


# `init` is a single leaf command (not a group), so register it directly rather than
# as a sub-Typer (add_typer would turn its positional PATH arg into a subcommand slot).
app.command("init", epilog=help_epilog(INIT_DOCS))(init_command)
app.add_typer(run, name="run", epilog=help_epilog(RUN_DOCS))
app.add_typer(gen, name="gen", epilog=help_epilog(GEN_DOCS))
app.add_typer(manifest, name="manifest", epilog=help_epilog(MANIFEST_DOCS))
app.add_typer(inspect, name="inspect", epilog=help_epilog(INSPECT_DOCS))
app.add_typer(call, name="call", epilog=help_epilog(CALL_DOCS))
