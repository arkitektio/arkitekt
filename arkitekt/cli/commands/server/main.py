import rich_click as click
from .init import init
from .up import up
from .down import down
from click import Context


@click.group()
@click.pass_context
def server(ctx: Context) -> None:
    """Manages your arkitekt deployments

    You can directly deploy your app to a server with the arkitekt server command. This will
    create a local docker-compose.yml file and a .arkitekt folder in your project. You can then
    use the arkitekt server build command to build your app for port and the arkitekt server run
    command to run your app on the server.

    """

    pass


server.add_command(init, "init")
server.add_command(up, "up")
server.add_command(down, "down")
