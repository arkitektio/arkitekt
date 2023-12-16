import rich_click as click
from .dev import dev
from .prod import prod


@click.group()
@click.pass_context
def run(ctx):
    """Runs your arkitekt app

    Running your app locally is the first step to developing your app. You can run your app in
    development mode, which will automatically reload your app when you change the code, or in
    production mode, which not reload your app when you change the code, but allows you to
    scale your app to multiple processes.



    """


run.add_command(dev, "dev")
run.add_command(prod, "prod")
