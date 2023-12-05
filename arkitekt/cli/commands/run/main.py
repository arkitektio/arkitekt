import rich_click as click
from .dev import dev
from .prod import prod


@click.group()
@click.pass_context
def run(ctx):
    """Runs the arkitekt app (using a builder) in stable mode

    You can choose between different builders to run your app. The default builder is the easy builder, which is
    designed to be easy to use and to get started with. It is not recommended to use this builder for
    production apps.

    """


run.add_command(dev, "dev")
run.add_command(prod, "prod")
