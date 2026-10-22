import typer

from arkitekt.cli.vars import get_console

from .init import GEN_HINT, init


gen = typer.Typer(invoke_without_command=True)


@gen.callback()
def gen_callback(ctx: typer.Context) -> None:
    """Code generation for Arkitekt Apps, with turms

    Code generation for API's is done with
    [link=https://github.com/jhnnsrs/turms]turms[/link], which arkitekt does not
    install or run. `arkitekt gen init` writes a GraphQL config for the services
    your app uses; write your operations, then run
    `uvx --with <service packages> turms gen` (or `turms watch`) in the app
    directory. turms imports each service's client while it generates.

    """
    if ctx.invoked_subcommand is None:
        get_console(ctx).print(GEN_HINT)


gen.command("init")(init)
