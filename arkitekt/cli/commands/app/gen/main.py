
import typer

from .watch import watch
from .compile import compile


gen = typer.Typer(no_args_is_help=True)


@gen.callback()
def gen_callback(ctx: typer.Context) -> None:
    """Codegeneration tools for Arkitekt Apps (requires turms)

    Code generation for API's is done with the help of GraphQL Code Generation
    that is powered by [link=https://github.com/jhnnsrs/turms]turms[/link]. Simply
    design your API in the documents folder and run `arkitekt gen compile` to
    create fully typed code for your API. You can also run `arkitekt gen watch`
    to automatically generate code when your documents change. This is useful
    for development.

    """


gen.command("watch")(watch)
gen.command("compile")(compile)
