import rich_click as click


import rich_click as click
from .variables import variables
from .definitions import definitions


@click.group()
@click.pass_context
def inspect(ctx):
    """Inspects your arkitekt app

    Inspects various parts of your arkitekt app. This is useful for debugging
    and development. It also represents methods that are called by the arkitekt
    server when you run your app in production mode.

    """


inspect.add_command(variables, "variables")
inspect.add_command(definitions, "definitions")
