import rich_click as click
from .build import build
from .publish import publish
from .stage import stage
from .wizard import wizard
from click import Context

@click.group()
@click.pass_context
def port(ctx: Context) -> None:
    """Deploy the arkitekt app with Port

    The port deployer is an arkitekt plugin service, which allows you to deploy your arkitekt app to
    any arkitekt instance and make it instantly available to the world. Port uses docker to containerize
    your application and will publish it locally to your dockerhub account, and mark it locally as
    deployed. People can then use your github repository to deploy your app to their arkitekt instance.

    """

    pass


port.add_command(build, "build")
port.add_command(publish, "publish")
port.add_command(stage, "stage")
port.add_command(wizard, "wizard")
