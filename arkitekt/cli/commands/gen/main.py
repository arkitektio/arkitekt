from typing import List
import rich_click as click
import shutil
from .watch import watch
from .compile import compile
from .init import init


@click.group()
def gen():
    """Use the arkitekt code generation modules to generate code"""
    try:
        import turms

        pass
    except ImportError as e:
        raise click.ClickException(
            "Turms is not installed. Please install turms first before using the arkitekt codegen."
        ) from e


gen.add_command(watch, "watch")
gen.add_command(compile, "compile")
gen.add_command(init, "init")
