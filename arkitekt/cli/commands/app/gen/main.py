import importlib.util

import typer

from arkitekt.cli.errors import cli_error
from .watch import watch
from .compile import compile
from .init import init


gen = typer.Typer(no_args_is_help=True)


@gen.callback()
def gen_callback(ctx: typer.Context) -> None:
    """Codegeneration tools for ArkitektNext Apps (requires turms)

    Code generation for API's is done with the help of GraphQL Code Generation
    that is powered by [link=https://github.com/jhnnsrs/turms]turms[/link]. Simply
    design your API in the documents folder and run `arkitekt gen compile` to
    create fully typed code for your API. You can also run `arkitekt gen watch`
    to automatically generate code when your documents change. This is useful
    for development.

    """
    if importlib.util.find_spec("turms") is None:
        cli_error(
            "Turms is not installed. Install it with: pip install 'arkitekt[cli]'"
        )


gen.command("watch")(watch)
gen.command("compile")(compile)
gen.command("init")(init)
