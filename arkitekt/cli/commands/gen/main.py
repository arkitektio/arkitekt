import rich_click as click
from .watch import watch
from .compile import compile
from .init import init


@click.group()
def gen():
    """Codegeneration tools for Arkitekt Apps (requires turms)

    Code generation for API's is done with the help of GraphQL Code Generation
    that is powered by [link=https://github.com/jhnnsrs/turms]turms[/link]. Simply
    design your API in the documents folder and run `arkitekt gen compile` to
    create fully typed code for your API. You can also run `arkitekt gen watch`
    to automatically generate code when your documents change. This is useful
    for development.

    """
    try:
        pass
    except ImportError as e:
        raise click.ClickException(
            "Turms is not installed. Please install turms first before using the arkitekt codegen."
        ) from e


gen.add_command(watch, "watch")
gen.add_command(compile, "compile")
gen.add_command(init, "init")
