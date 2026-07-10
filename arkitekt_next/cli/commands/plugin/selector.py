from typing import Annotated, Optional
import typer
from arkitekt_next.cli.errors import cli_error
from arkitekt_next.cli.interactive import require_interactive
from arkitekt_next.cli.vars import get_work_dir
from arkitekt_next.utils import create_arkitekt_next_folder
import os


selector = typer.Typer(no_args_is_help=True, help="Manage selectors")


def add_selector(
    ctx: typer.Context,
    flavour: Annotated[str, typer.Argument()],
    kind: Annotated[
        Optional[str],
        typer.Option("--kind", "-k", help="The kind of selector"),
    ] = None,
    api_version: Annotated[
        Optional[str],
        typer.Option("--api-version", "-av", help="The api version of the selector"),
    ] = None,
    api_thing: Annotated[
        Optional[str],
        typer.Option("--api-thing", "-at", help="The api thing of the selector"),
    ] = None,
    one_api_version: Annotated[
        Optional[str],
        typer.Option(
            "--one-api-version", "-oav", help="The one api version of the selector"
        ),
    ] = None,
    cuda_cores: Annotated[
        Optional[int],
        typer.Option("--cuda-cores", "-cc", help="The cuda cores of the selector"),
    ] = None,
    frequency: Annotated[
        Optional[int],
        typer.Option("--frequency", "-fr", help="The frequency of the selector"),
    ] = None,
    memory: Annotated[
        Optional[int],
        typer.Option("--memory", "-m", help="The memory of the selector"),
    ] = None,
) -> None:
    """Add a new selector to a flavour."""
    import yaml
    from kabinet.api.schema import SelectorInput
    from .types import Flavour

    work_dir = get_work_dir(ctx)
    arkitekt_next_folder = create_arkitekt_next_folder(base_dir=work_dir)
    flavour_folder = os.path.join(arkitekt_next_folder, "flavours", flavour)
    config_file = os.path.join(flavour_folder, "config.yaml")

    if not os.path.exists(config_file):
        cli_error(f"Flavour {flavour} does not exist")

    if kind is None:
        require_interactive(
            "Choosing a selector kind",
            hint="Pass --kind to set it non-interactively.",
        )
        kind = typer.prompt("The kind of selector")

    with open(config_file, "r") as f:
        data = yaml.safe_load(f)

    fl = Flavour(**data)

    new_selector = SelectorInput(
        kind=kind,
        apiVersion=api_version,
        apiThing=api_thing,
        oneapiVersion=one_api_version,
        cudaCores=cuda_cores,
        frequency=frequency,
        memory=memory,
    )

    fl.selectors.append(new_selector)

    with open(config_file, "w") as f:
        yaml.dump(fl.model_dump(), f)

    typer.echo(f"Added selector {new_selector} to flavour {flavour}")


selector.command("add")(add_selector)
