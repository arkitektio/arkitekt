from typing import Annotated, Optional
import typer
from arkitekt_next.cli.errors import cli_error
from arkitekt_next.cli.interactive import require_interactive
from arkitekt_next.cli.vars import get_console, get_work_dir
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
    from kabinet.api.schema import (
        CpuSelectorInput,
        CudaSelectorInput,
        OneApiSelectorInput,
        RocmSelectorInput,
    )
    from .types import Flavour

    console = get_console(ctx)
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

    # SelectorInput is a @oneOf union discriminated on `kind`: construct the
    # matching variant with only the fields that variant carries.
    if kind == "cpu":
        new_selector = CpuSelectorInput(kind="cpu", frequency=frequency, memory=memory)
    elif kind == "cuda":
        new_selector = CudaSelectorInput(
            kind="cuda", cuda_version=api_version, cuda_cores=cuda_cores
        )
    elif kind == "oneapi":
        new_selector = OneApiSelectorInput(kind="oneapi", oneapi_version=one_api_version)
    elif kind == "rocm":
        new_selector = RocmSelectorInput(
            kind="rocm", api_version=api_version, api_thing=api_thing
        )
    else:
        cli_error(f"Unknown selector kind '{kind}'. Available: cpu, cuda, oneapi, rocm")

    fl.selectors.append(new_selector)

    with open(config_file, "w") as f:
        yaml.dump(fl.model_dump(), f)

    console.print(f"Added selector {new_selector} to flavour [bold]{flavour}[/bold]")


selector.command("add")(add_selector)
