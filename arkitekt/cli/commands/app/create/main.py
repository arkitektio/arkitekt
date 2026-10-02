import enum
import os
import shutil
import subprocess
from getpass import getuser
from typing import Annotated, List, Optional

import typer
import semver

from arkitekt.cli.constants import compile_scopes
from arkitekt.cli.validators import validate_scopes, validate_template
from arkitekt.cli.errors import cli_error
from arkitekt.cli.tty import require_tty
from arkitekt.cli.ui import done, escape, notice
from arkitekt.cli.utils import build_relative_dir
from arkitekt.cli.vars import get_console, get_work_dir


#: Non-interactive escape hatch surfaced when `create` needs to prompt.
_CREATE_HINT = "Pass --yes to accept the defaults, or provide the fields as options."


def get_default_package_manager():
    if shutil.which("uv"):
        return "uv"
    return "pip"


class PackageManager(str, enum.Enum):
    """The package managers supported by ``create``."""

    pip = "pip"
    uv = "uv"


#: The placeholder in a template that becomes the ``App(...)`` arguments.
APP_ARGUMENTS_PLACEHOLDER = "__APP_ARGUMENTS__"


def render_app_arguments(
    identifier: str,
    version: str,
    author: Optional[str] = None,
    scopes: Optional[List[str]] = None,
    logo: Optional[str] = None,
) -> str:
    """The ``App(...)`` arguments that declare the app's identity, as Python source.

    Built with ``repr`` so any identifier or author quotes correctly. The identity
    lives in the code this writes, not in a project file next to it.
    """
    arguments = [repr(identifier), repr(version)]
    if author:
        arguments.append(f"author={author!r}")
    if scopes:
        arguments.append(
            f"scopes={list(scopes)!r}"
        )  # lets forget scopes as of now, i would like to have them be infered in the future from which service actions are needed (because scopes are service specific)
    if logo:
        arguments.append(f"logo={logo!r}")
    return ", ".join(arguments)


def render_template(template_source: str, app_arguments: str) -> str:
    """Fill a template's ``App(...)`` placeholder.

    A plain replace, not ``str.format``: the templates' docstrings carry
    ``{{n}}``-style port references that rekuest reads, and formatting would
    rewrite them.
    """
    if APP_ARGUMENTS_PLACEHOLDER not in template_source:
        raise ValueError(
            f"The template has no {APP_ARGUMENTS_PLACEHOLDER} placeholder."
        )
    return template_source.replace(APP_ARGUMENTS_PLACEHOLDER, app_arguments)


def create_command(
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
            help=f"The scopes of the app. You can choose multiple for your app. Available: {', '.join(compile_scopes())}",
            callback=validate_scopes,
        ),
    ] = ["read"],
    template: Annotated[
        str,
        typer.Option(
            "--template",
            "-t",
            help="The template to use. You can choose from a variety of preconfigured templates. They are just starting points and can be changed later.",
            callback=validate_template,
        ),
    ] = "simple",
    entrypoint: Annotated[
        Optional[str],
        typer.Option(
            "--entrypoint",
            "-e",
            help="The name of the python file to create, without the .py ending. Commands find the app in it through their 'module[:attr]' target, which defaults to 'app'.",
        ),
    ] = None,
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
    """Creates an Arkitekt app in this folder

    This command will create a new Arkitekt app in the current directory: an
    `app.py` file (or the --entrypoint you choose) that declares the app with
    `App(...)`, carrying its identifier, version, author, scopes and logo. That
    file is the whole app; there is no separate manifest. By default, the app will
    be created as a simple hello world app, but you can choose from a
    variety of templates.

    """

    # Resolve at runtime (not at import) so auto-detection respects the current env.
    manager = (
        package_manager.value if package_manager is not None else get_default_package_manager()
    )

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
            require_tty("`create`", hint=_CREATE_HINT)
            identifier = str(typer.prompt("Your app identifier", default=default_identifier))

    if not author:
        if yes:
            author = getuser()
        else:
            require_tty("`create`", hint=_CREATE_HINT)
            author = str(typer.prompt("Your name", default=getuser()))

    if not entrypoint:
        if yes:
            entrypoint = "app"
        else:
            require_tty("`create`", hint=_CREATE_HINT)
            entrypoint = str(typer.prompt("Your app file", default="app"))
    entrypoint = entrypoint.removesuffix(".py")

    if not semver.Version.is_valid(version):
        if yes:
            cli_error(
                f"Invalid version: {version}. Arkitekt versions need to follow semver."
            )
        else:
            require_tty("`create`", hint=_CREATE_HINT)
            while not semver.Version.is_valid(version):
                get_console(ctx).print(
                    "Arkitekt versions need to follow [link=https://semver.org]semver[/link]. Please choose a correct format (examples: 0.0.0, 0.1.0, 0.0.0-alpha.1)"
                )
                version = str(
                    typer.prompt(
                        "The version of your app",
                        default="0.0.1",
                    )
                )

    if manager == "uv":
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
            package_spec = f"arkitekt[{extras_string}]" if with_extra else "arkitekt"
            subprocess.run(["uv", "add", package_spec], check=True, cwd=work_dir)
            hello_py = os.path.join(work_dir, "hello.py")
            if os.path.exists(hello_py) and entrypoint != "hello":
                os.remove(hello_py)
        else:
            console.print(
                "pyproject.toml already exists. Skipping uv init.", style="yellow"
            )

    with open(build_relative_dir("templates", f"{template}.py")) as f:
        template_app = render_template(
            f.read(),
            render_app_arguments(
                identifier, version, author=author, scopes=scopes, logo=logo
            ),
        )

    entrypoint_file = os.path.join(work_dir, f"{entrypoint}.py")
    if os.path.exists(entrypoint_file) and not overwrite_app:
        if yes:
            should_overwrite = True
        else:
            require_tty("`create`", hint=_CREATE_HINT)
            should_overwrite = typer.confirm(
                "Entrypoint File already exists. Do you want to overwrite?"
            )
        if should_overwrite:
            with open(entrypoint_file, "w") as f:
                f.write(template_app)
    else:
        with open(entrypoint_file, "w") as f:
            f.write(template_app)

    run_hint = (
        "arkitekt run dev" if entrypoint == "app" else f"arkitekt run dev {entrypoint}"
    )
    by = f" · {escape(author)}" if author else ""
    done(
        console,
        f"{escape(identifier)} {escape(version)}{by} was created in "
        f"{escape(os.path.basename(entrypoint_file))}",
    )
    notice(console, f"Start it with `{run_hint}`. We are excited to see what you come up with!")


