import enum
import os
import shutil
import subprocess
from getpass import getuser
from typing import Annotated, List, Optional

import typer
import semver
from rich.panel import Panel

from arkitekt.cli.constants import compile_scopes, compile_templates
from arkitekt.cli.errors import cli_error, confirm_or_abort
from arkitekt.cli.interactive import require_interactive
from arkitekt.cli.io import load_manifest, write_manifest
from arkitekt.cli.types import Manifest
from arkitekt.cli.utils import build_relative_dir
from arkitekt.cli.vars import get_console, get_work_dir


#: Non-interactive escape hatch surfaced when `init` needs to prompt.
_INIT_HINT = "Pass --yes to accept the defaults, or provide the fields as options."


def get_default_package_manager():
    if shutil.which("uv"):
        return "uv"
    return "pip"


class PackageManager(str, enum.Enum):
    """The package managers supported by ``init``."""

    pip = "pip"
    uv = "uv"


def _validate_template(value: str) -> str:
    valid = compile_templates()
    if value not in valid:
        raise typer.BadParameter(
            f"'{value}' is not one of {', '.join(valid)}."
        )
    return value


def _validate_scopes(value: List[str]) -> List[str]:
    valid = compile_scopes()
    for scope in value:
        if scope not in valid:
            raise typer.BadParameter(
                f"'{scope}' is not one of {', '.join(valid)}."
            )
    return value


def init_command(
    ctx: typer.Context,
    path: Annotated[str, typer.Argument()] = ".",
    identifier: Annotated[
        Optional[str],
        typer.Option(
            "--identifier",
            "-i",
            help="The identifier of your app. This will be used to identify your app in the Arkitekt ecosystem. It should be unique and should follow the [link=https://en.wikipedia.org/wiki/Reverse_domain_name_notation]reverse domain name notation[/link] (example: com.example.myapp)",
        ),
    ] = None,
    version: Annotated[
        str,
        typer.Option(
            "--version",
            "-v",
            help="The version of your app. Needs to follow [link=https://semver.org/]semantic versioning[/link].",
        ),
    ] = "0.0.1",
    author: Annotated[
        Optional[str],
        typer.Option(
            "--author",
            help="The author of your app. This will be shown to users of your app",
        ),
    ] = None,
    logo: Annotated[
        Optional[str],
        typer.Option(
            "--logo",
            help="Which logo to use for this app, needs to be a valid url",
        ),
    ] = None,
    scopes: Annotated[
        List[str],
        typer.Option(
            "--scopes",
            "-s",
            help="The scopes of the app. You can choose multiple for your app. For a list of scopes, run `arkitekt manifest scopes available`",
            callback=_validate_scopes,
        ),
    ] = ["read"],
    template: Annotated[
        str,
        typer.Option(
            "--template",
            "-t",
            help="The template to use. You can choose from a variety of preconfigured templates. They are just starting points and can be changed later.",
            callback=_validate_template,
        ),
    ] = "simple",
    entrypoint: Annotated[
        Optional[str],
        typer.Option(
            "--entrypoint",
            "-e",
            help="The entrypoint of your app. This will be the name of the python file. Omit the .py ending",
        ),
    ] = None,
    overwrite_manifest: Annotated[
        bool,
        typer.Option(
            "--overwrite-manifest",
            "-om",
            help="Should we overwrite the existing manifest if it already exists?",
        ),
    ] = False,
    overwrite_app: Annotated[
        bool,
        typer.Option(
            "--overwrite-app",
            "-oa",
            help="Do you want to overwrite the app file if it exists?",
        ),
    ] = False,
    package_manager: Annotated[
        Optional[PackageManager],
        typer.Option(
            "--package-manager",
            "-pm",
            help="The package manager to use. If uv is selected, it will initialize a project with uv.",
        ),
    ] = None,
    yes: Annotated[
        bool,
        typer.Option(
            "--yes",
            "-y",
            help="Automatically accept defaults",
        ),
    ] = False,
    with_extra: Annotated[
        List[str],
        typer.Option(
            "--with-extra",
            help="The extras to install with arkitekt. Defaults to all.",
        ),
    ] = ["all"],
):
    """Initializes an Arkitekt app

    This command will create a new Arkitekt app in the current directory. It will
    create a `.arkitekt` folder that will contain a manifest and a `app.py` file,
    which will serve as the entrypoint for your app. By default, the app will be
    initialized with a simple hello world app, but you can choose from a variety
    of templates.

    """

    # Resolve at runtime (not at import) so auto-detection respects the current env.
    package_manager = package_manager.value if package_manager is not None else get_default_package_manager()

    console = get_console(ctx)
    parent_work_dir = get_work_dir(ctx)

    # Resolve the target directory without changing process CWD
    if path != ".":
        work_dir = os.path.join(parent_work_dir, path)
        os.makedirs(work_dir, exist_ok=True)
    else:
        work_dir = parent_work_dir

    if not identifier:
        default_identifier = os.path.basename(work_dir)
        if yes:
            identifier = default_identifier
        else:
            require_interactive("`init`", hint=_INIT_HINT)
            identifier = typer.prompt("Your app identifier", default=default_identifier)

    if not author:
        if yes:
            author = getuser()
        else:
            require_interactive("`init`", hint=_INIT_HINT)
            author = typer.prompt("Your name", default=getuser())

    if not entrypoint:
        if yes:
            entrypoint = "app"
        else:
            require_interactive("`init`", hint=_INIT_HINT)
            entrypoint = typer.prompt("Your app file", default="app")

    if not semver.Version.is_valid(version):
        if yes:
            cli_error(
                f"Invalid version: {version}. Arkitekt versions need to follow semver."
            )
        else:
            require_interactive("`init`", hint=_INIT_HINT)
            while not semver.Version.is_valid(version):
                get_console(ctx).print(
                    "Arkitekt versions need to follow [link=https://semver.org]semver[/link]. Please choose a correct format (examples: 0.0.0, 0.1.0, 0.0.0-alpha.1)"
                )
                version = typer.prompt(
                    "The version of your app",
                    default="0.0.1",
                )

    existing_manifest = load_manifest(base_dir=work_dir)
    if existing_manifest and not overwrite_manifest:
        if yes:
            should_overwrite = True
        else:
            require_interactive("`init`", hint=_INIT_HINT)
            confirm_or_abort(
                f"Another Arkitekt app {existing_manifest.to_console_string()} exists already at {work_dir}?. Do you want to overwrite?"
            )
            should_overwrite = True
        if not should_overwrite:
            ctx.abort()

    manifest = Manifest(
        logo=logo,
        author=author,
        identifier=identifier,
        version=version,
        scopes=scopes,
        entrypoint=entrypoint,
        package_manager=package_manager,
    )

    if package_manager == "uv":
        if not shutil.which("uv"):
            cli_error(
                "uv is not installed. Please install uv or choose another package manager."
            )

        pyproject = os.path.join(work_dir, "pyproject.toml")
        if not os.path.exists(pyproject):
            subprocess.run(
                ["uv", "init", "--name", identifier, "--no-workspace"],
                check=True,
                cwd=work_dir,
            )
            extras_string = ",".join(with_extra)
            package_spec = (
                f"arkitekt[{extras_string}]" if with_extra else "arkitekt"
            )
            subprocess.run(["uv", "add", package_spec], check=True, cwd=work_dir)
            hello_py = os.path.join(work_dir, "hello.py")
            if os.path.exists(hello_py) and entrypoint != "hello":
                os.remove(hello_py)
        else:
            console.print(
                "pyproject.toml already exists. Skipping uv init.", style="yellow"
            )

    with open(build_relative_dir("templates", f"{template}.py")) as f:
        template_app = f.read()

    entrypoint_file = os.path.join(work_dir, f"{entrypoint}.py")
    if os.path.exists(entrypoint_file) and not overwrite_app:
        if yes:
            should_overwrite = True
        else:
            require_interactive("`init`", hint=_INIT_HINT)
            should_overwrite = typer.confirm(
                "Entrypoint File already exists. Do you want to overwrite?"
            )
        if should_overwrite:
            with open(entrypoint_file, "w") as f:
                f.write(template_app)
    else:
        with open(entrypoint_file, "w") as f:
            f.write(template_app)

    write_manifest(manifest, base_dir=work_dir)
    md = Panel(
        f"{manifest.to_console_string()} was successfully initialized\n\n"
        + "[not bold white]We are excited to see what you come up with!",
        border_style="green",
        style="green",
    )
    console.print(md)


init = typer.Typer(help=init_command.__doc__)
init.command()(init_command)
