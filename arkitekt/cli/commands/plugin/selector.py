from typing import Annotated, Optional
import typer
from arkitekt.cli.errors import cli_error
from arkitekt.cli.interactive import require_interactive
from arkitekt.cli.vars import get_console, get_work_dir
from arkitekt.utils import create_arkitekt_folder
import os


selector = typer.Typer(no_args_is_help=True, help="Manage selectors")

KINDS = "cpu, ram, cuda, rocm, oneapi, label"


def add_selector(
    ctx: typer.Context,
    flavour: Annotated[str, typer.Argument()],
    kind: Annotated[
        Optional[str],
        typer.Option("--kind", "-k", help=f"The kind of selector ({KINDS})"),
    ] = None,
    required: Annotated[
        bool,
        typer.Option(
            "--required/--optional",
            help="Required selectors are hard constraints; optional ones are preferences scored by --weight.",
        ),
    ] = True,
    weight: Annotated[
        Optional[int],
        typer.Option("--weight", "-w", help="Scoring weight of an optional selector."),
    ] = None,
    # cpu
    min_count: Annotated[
        Optional[int],
        typer.Option("--min-count", help="cpu: the minimum number of CPU cores."),
    ] = None,
    frequency: Annotated[
        Optional[float],
        typer.Option("--frequency", "-fr", help="cpu: the minimum CPU frequency, in MHz."),
    ] = None,
    arch: Annotated[
        Optional[str],
        typer.Option("--arch", help="cpu: the CPU architecture of the image (amd64, arm64, ...)."),
    ] = None,
    # ram
    memory: Annotated[
        Optional[int],
        typer.Option("--memory", "-m", help="ram: the minimum system memory, in MB."),
    ] = None,
    # cuda
    compute_capability: Annotated[
        Optional[str],
        typer.Option("--compute-capability", help="cuda: the minimum CUDA compute capability (e.g. 8.6)."),
    ] = None,
    cuda_version: Annotated[
        Optional[str],
        typer.Option("--cuda-version", help="cuda: the minimum CUDA driver/runtime version."),
    ] = None,
    vram: Annotated[
        Optional[int],
        typer.Option("--vram", help="cuda: the minimum GPU memory (VRAM), in MB."),
    ] = None,
    count: Annotated[
        Optional[int],
        typer.Option("--count", help="cuda: the number of GPUs required."),
    ] = None,
    cuda_cores: Annotated[
        Optional[int],
        typer.Option("--cuda-cores", "-cc", help="cuda: deprecated, prefer --compute-capability and --vram."),
    ] = None,
    # rocm
    api_version: Annotated[
        Optional[str],
        typer.Option("--api-version", "-av", help="rocm: the minimum ROCm API version."),
    ] = None,
    api_thing: Annotated[
        Optional[str],
        typer.Option("--api-thing", "-at", help="rocm: an additional ROCm capability qualifier."),
    ] = None,
    # oneapi
    one_api_version: Annotated[
        Optional[str],
        typer.Option("--one-api-version", "-oav", help="oneapi: the minimum oneAPI version."),
    ] = None,
    # label
    key: Annotated[
        Optional[str],
        typer.Option("--key", help="label: the qualifier key the backend resource must carry."),
    ] = None,
    value: Annotated[
        Optional[str],
        typer.Option("--value", help="label: the qualifier value; omit to only require the key to exist."),
    ] = None,
) -> None:
    """Add a selector (a hardware/capability placement requirement) to a flavour.

    Selectors constrain hardware placement only — a service your app needs is
    a requirement, never a selector.
    """
    import yaml
    from kabinet.api.schema import (
        CpuSelectorInput,
        CudaSelectorInput,
        LabelSelectorInput,
        OneApiSelectorInput,
        RamSelectorInput,
        RocmSelectorInput,
    )
    from .types import Flavour

    console = get_console(ctx)
    work_dir = get_work_dir(ctx)
    arkitekt_folder = create_arkitekt_folder(base_dir=work_dir)
    flavour_folder = os.path.join(arkitekt_folder, "flavours", flavour)
    config_file = os.path.join(flavour_folder, "config.yaml")

    if not os.path.exists(config_file):
        cli_error(f"Flavour {flavour} does not exist")

    if kind is None:
        require_interactive(
            "Choosing a selector kind",
            hint="Pass --kind to set it non-interactively.",
        )
        kind = typer.prompt(f"The kind of selector ({KINDS})")

    with open(config_file, "r") as f:
        data = yaml.safe_load(f)

    fl = Flavour(**data)

    shared = {"required": required}
    if weight is not None:
        shared["weight"] = weight

    # SelectorInput is a @oneOf union discriminated on `kind`: construct the
    # matching variant with only the fields that variant carries.
    if kind == "cpu":
        new_selector = CpuSelectorInput(
            min_count=min_count, frequency=frequency, arch=arch, **shared
        )
    elif kind == "ram":
        new_selector = RamSelectorInput(min=memory, **shared)
    elif kind == "cuda":
        new_selector = CudaSelectorInput(
            compute_capability=compute_capability,
            cuda_version=cuda_version,
            memory=vram,
            count=count,
            cuda_cores=cuda_cores,
            **shared,
        )
    elif kind == "rocm":
        new_selector = RocmSelectorInput(
            api_version=api_version, api_thing=api_thing, **shared
        )
    elif kind == "oneapi":
        new_selector = OneApiSelectorInput(oneapi_version=one_api_version, **shared)
    elif kind == "label":
        if key is None:
            cli_error("A label selector needs --key")
        new_selector = LabelSelectorInput(key=key, value=value, **shared)
    else:
        cli_error(f"Unknown selector kind '{kind}'. Available: {KINDS}")

    fl.selectors.append(new_selector)

    with open(config_file, "w") as f:
        yaml.dump(fl.model_dump(), f)

    console.print(f"Added selector {new_selector} to flavour [bold]{flavour}[/bold]")


selector.command("add")(add_selector)
