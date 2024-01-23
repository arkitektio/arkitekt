import rich_click as click
from .constants import *
from .types import *
from .vars import *
from .ui import *

with_fakts_url = click.option(
    "--url",
    "-u",
    help="The fakts url for connection",
    default="http://localhost:8000",
    envvar="FAKTS_URL",
)

with_token = click.option(
    "--token",
    "-t",
    help="The token for the fakts instance",
    envvar="FAKTS_TOKEN",
    required=False,
)
with_version = click.option(
    "--version",
    "-v",
    help="Override the version of the app",
    envvar="ARKITEKT_VERSION",
)

with_log_level = click.option(
    "--log",
    "-l",
    help="Override the logging level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]),
    envvar="ARKITEKT_LOG_LEVEL",
)


with_skip_cache = click.option(
    "--no-cache",
    "-nc",
    is_flag=True,
    default=False,
    help="Should we skip the cache",
    envvar="ARKITEKT_NO_CACHE",
)

with_instance_id = click.option(
    "--instance-id",
    "-i",
    default="main",
    help="The token for the fakts instance",
    envvar="REKUEST_INSTANCE",
)

with_log_level = click.option(
    "--log-level",
    "-l",
    default="ERROR",
    help="The token for the fakts instance",
    envvar="ARKITEKT_LOG_LEVEL",
)


with_builder = click.option(
    "--builder",
    "-b",
    default="arkitekt.builders.easy",
    help="The builder for this run",
    envvar="ARKITEKT_BUILDER",
)

with_headless = click.option(
    "--headless",
    "-h",
    is_flag=True,
    default=False,
    help="Should we start headless",
    envvar="ARKITEKT_HEADLESS",
)


def check_gen_boring(ctx, param, value):
    """Callback to check and prompt for file overwrite."""

    if not value:
        get_console(ctx).print(construct_codegen_welcome_panel())

    return value


with_boring = click.option(
    "--boring",
    help="Should we skip the welcome message?",
    is_flag=True,
    default=False,
    callback=check_gen_boring,
)
with_seperate_document_dirs = click.option(
    "--seperate-doc-dirs",
    "-sd",
    help="Should we generate seperate dirs for the documents?",
    is_flag=True,
    default=False,
)
with_choose_services = click.option(
    "--services",
    "-s",
    help="The services to create the codegen for",
    multiple=True,
    type=click.Choice(compile_services()),
    default=["mikro"],
)
with_graphql_config = click.option(
    "--config",
    "-c",
    help="The name of the configuration file",
    type=str,
    default="graphql.config.yaml",
)
with_api_path = click.option(
    "--path",
    "-c",
    help="The path of the api to be generated",
    prompt="Where should we generate the api? (relative to the current directory)",
    type=str,
    default="api",
)


def check_overwrite_config(ctx, param, value):
    """Callback to check and prompt for file overwrite."""

    config = ctx.params["config"]
    if os.path.exists(config) and not value:
        should_overwrite = click.confirm(
            "GraphQL Config file already exists. Do you want to overwrite?"
        )
        return should_overwrite

    return value


with_overwrite_graphql = click.option(
    "--overwrite-config",
    "-o",
    help="Should we overwrite the config file if it already exists",
    is_flag=True,
    default=False,
    callback=check_overwrite_config,
)
with_documents = click.option(
    "--documents",
    "-d",
    help="With documents",
    is_flag=True,
    default=True,
)
with_schemas = click.option(
    "--schemas",
    "-s",
    help="Should we copy the schemas",
    is_flag=True,
    default=True,
)
