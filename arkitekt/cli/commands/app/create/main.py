import enum
import os
import shutil
import subprocess
from dataclasses import dataclass
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


class Forge(str, enum.Enum):
    """Where ``create`` can have the app released from."""

    github = "github"
    gitlab = "gitlab"
    none = "none"


@dataclass(frozen=True)
class ProjectTemplate:
    """What ``create`` sets up unless told otherwise. Every part has its own option."""

    summary: str
    #: Create the app in a folder of its own, rather than in the one it is run from.
    new_folder: bool
    #: The package manager; ``None`` takes uv when it is installed, else pip.
    package_manager: Optional[str]
    #: Write a flavour, so the app can be built into an image.
    flavour: bool
    #: The forge that releases the app on every push.
    ci: Forge
    #: Write a first test of the starter's actions.
    tests: bool = False
    #: The code the app file starts with.
    starter: str = "simple"


TEMPLATES = {
    "project": ProjectTemplate(
        "a new folder holding a uv project, an app that makes and blurs images, its tests, a flavour, "
        "and a GitHub workflow that releases it with semantic-release",
        new_folder=True,
        package_manager="uv",
        flavour=True,
        ci=Forge.github,
        tests=True,
        starter="image",
    ),
    "blok": ProjectTemplate(
        "a project like 'project', whose app is a blok agent: it analyses images and shows what it finds "
        "in a panel of its own, drawn by the user interface",
        new_folder=True,
        package_manager="uv",
        flavour=True,
        ci=Forge.github,
        tests=True,
        starter="blok",
    ),
    "qt": ProjectTemplate(
        "a new folder holding a uv project and a desktop app with a window of its own (Qt), and its tests; "
        "no flavour and no workflow, as a desktop app is not released as an image",
        new_folder=True,
        package_manager="uv",
        flavour=False,
        ci=Forge.none,
        tests=True,
        starter="qt",
    ),
    "bare": ProjectTemplate(
        "only the app file, in this folder",
        new_folder=False,
        package_manager=None,
        flavour=False,
        ci=Forge.none,
    ),
}

#: The template `create` uses when none is named.
DEFAULT_TEMPLATE = "project"


def validate_project_template(value: str) -> str:
    """Check ``--template`` against the project templates."""
    if value not in TEMPLATES:
        raise typer.BadParameter(f"'{value}' is not one of {', '.join(TEMPLATES)}.")
    return value


def validate_starter(value: Optional[str]) -> Optional[str]:
    """Check ``--starter`` against the starters, when one is named."""
    return None if value is None else validate_template(value)


#: The extras a starter cannot do without, beside the ones asked for.
STARTER_EXTRAS = {"image": "mikro", "blok": "mikro", "qt": "qt"}

#: The extras of those that `all` does not bring: it bundles the service clients
#: and the runtime, not the Qt integration.
EXTRAS_BESIDE_ALL = {"qt"}

#: How a starter is started, when it is not by `arkitekt run dev`: a Qt app is a
#: program with a window, and runs itself.
STARTER_COMMANDS = {"qt": "python {entrypoint}.py"}

#: What a starter still needs before it starts, that `create` leaves to its author.
STARTER_NEEDS = {
    "qt": (
        "A Qt app needs a Qt binding",
        "none is installed, the choice is yours: `{add} pyqt6` (or pyside6)",
    ),
}


def needs_extra(extra: str, asked_for: List[str]) -> bool:
    """Whether a starter's extra has to be added to the ones asked for."""
    if extra in asked_for:
        return False
    return extra in EXTRAS_BESIDE_ALL or "all" not in asked_for

DEFAULT_BRANCH = "main"


def start_on_default_branch(work_dir: str) -> None:
    """Put a repository that has no commit yet on `main`.

    `uv init` creates the repository on whatever branch git is configured to start
    with, which is `master` unless the user changed it.
    """
    try:
        subprocess.run(
            ["git", "symbolic-ref", "HEAD", f"refs/heads/{DEFAULT_BRANCH}"],
            cwd=work_dir,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    except OSError:
        pass


CONFTEST = '''"""Loads arkitekt's test fixtures: `call` and `teststack`, and the app they call."""
{environment}
import sys
from pathlib import Path

# The app is a module of the project, not of tests/: a test imports it from there.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

pytest_plugins = ["arkitekt.testing"]
'''

#: What points the fixtures at an app that is not in ``app.py``.
CONFTEST_TARGET = '''
import os

os.environ.setdefault("ARKITEKT_APP", "{entrypoint}")
'''

#: What the file of a starter's tests against a hub is called after, beside the one with no server.
HUB_TESTS_SUFFIX = "_hub"

#: The placeholder in a starter's tests that becomes the module the app is in.
ENTRYPOINT_PLACEHOLDER = "__ENTRYPOINT__"

#: Keeps a bare `pytest` to the tests that need no server: the last `-m` wins, so
#: `pytest -m hub` still selects the ones that run against a hub.
PYTEST_OPTIONS = '''
[tool.pytest.ini_options]
addopts = "-m 'not hub'"
'''


def write_pytest_options(work_dir: str) -> bool:
    """Have a bare ``pytest`` leave the hub tests out, in a project that says nothing of pytest yet."""
    path = os.path.join(work_dir, "pyproject.toml")
    if not os.path.exists(path):
        return False
    with open(path) as file:
        if "[tool.pytest" in file.read():
            return False
    with open(path, "a") as file:
        file.write(PYTEST_OPTIONS)
    return True


def write_tests(work_dir: str, starter: str, entrypoint: str = "app") -> Optional[str]:
    """Write a first test of the starter's actions, unless the project has tests already.

    Args:
        work_dir: The project directory.
        starter: The starter the app was made from; its tests are the ones written.
        entrypoint: The module the app is in.

    Returns:
        The test file, relative to ``work_dir``, or ``None`` if ``tests/`` was there.
    """
    tests_dir = os.path.join(work_dir, "tests")
    if os.path.exists(tests_dir):
        return None
    os.makedirs(tests_dir)
    environment = "" if entrypoint == "app" else CONFTEST_TARGET.format(entrypoint=entrypoint)
    with open(os.path.join(tests_dir, "conftest.py"), "w") as file:
        file.write(CONFTEST.format(environment=environment))
    relative = os.path.join("tests", f"test_{entrypoint}.py")
    # A starter that uses a service has two: one with no server, and one against a hub.
    for suffix in ("", HUB_TESTS_SUFFIX):
        source_path = build_relative_dir("starter_tests", f"{starter}{suffix}.py")
        if not os.path.exists(source_path):
            continue
        with open(source_path) as source:
            with open(os.path.join(tests_dir, f"test_{entrypoint}{suffix}.py"), "w") as file:
                file.write(source.read().replace(ENTRYPOINT_PLACEHOLDER, entrypoint))
    return relative


def hub_tests(work_dir: str, entrypoint: str = "app") -> Optional[str]:
    """The project's tests against a hub, relative to ``work_dir``, if it has any."""
    relative = os.path.join("tests", f"test_{entrypoint}{HUB_TESTS_SUFFIX}.py")
    return relative if os.path.exists(os.path.join(work_dir, relative)) else None


def current_branch(work_dir: str) -> str:
    """The branch a fresh project is on, which is the one its pushes will come from."""
    try:
        result = subprocess.run(
            ["git", "symbolic-ref", "--short", "HEAD"],
            cwd=work_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=False,
        )
    except OSError:
        return DEFAULT_BRANCH
    return result.stdout.strip() if result.returncode == 0 and result.stdout.strip() else DEFAULT_BRANCH


#: The placeholder in a template that becomes the ``App(...)`` arguments.
APP_ARGUMENTS_PLACEHOLDER = "__APP_ARGUMENTS__"

#: The placeholder in a template that becomes the app's version, where the
#: template keeps it in a variable of its own.
APP_VERSION_PLACEHOLDER = "__APP_VERSION__"

#: The variable a starter keeps its version in: what semantic-release raises.
VERSION_VARIABLE = "__version__"


def render_app_arguments(
    identifier: str,
    version: str,
    author: Optional[str] = None,
    scopes: Optional[List[str]] = None,
    logo: Optional[str] = None,
    version_variable: Optional[str] = None,
) -> str:
    """The ``App(...)`` arguments that declare the app's identity, as Python source.

    Built with ``repr`` so any identifier or author quotes correctly. The identity
    lives in the code this writes, not in a project file next to it.

    Args:
        version_variable: The variable the template keeps the version in; the
            app is then declared with it, not with the version written out.
    """
    arguments = [repr(identifier), version_variable or repr(version)]
    if author:
        arguments.append(f"author={author!r}")
    if scopes:
        arguments.append(
            f"scopes={list(scopes)!r}"
        )  # lets forget scopes as of now, i would like to have them be infered in the future from which service actions are needed (because scopes are service specific)
    if logo:
        arguments.append(f"logo={logo!r}")
    return ", ".join(arguments)


def render_template(template_source: str, app_arguments: str, version: Optional[str] = None) -> str:
    """Fill a template's ``App(...)`` placeholder, and its version's if it has one.

    A plain replace, not ``str.format``: a template is Python source, and
    formatting would trip over every brace in it.
    """
    if APP_ARGUMENTS_PLACEHOLDER not in template_source:
        raise ValueError(
            f"The template has no {APP_ARGUMENTS_PLACEHOLDER} placeholder."
        )
    rendered = template_source.replace(APP_ARGUMENTS_PLACEHOLDER, app_arguments)
    if APP_VERSION_PLACEHOLDER in rendered:
        if version is None:
            raise ValueError(f"The template has an {APP_VERSION_PLACEHOLDER} placeholder, and no version was given.")
        # Double quotes: what semantic-release writes back, so a release changes one number.
        rendered = rendered.replace(APP_VERSION_PLACEHOLDER, f'"{version}"')
    return rendered


def render_starter(
    starter: str,
    identifier: str,
    version: str,
    author: Optional[str] = None,
    scopes: Optional[List[str]] = None,
    logo: Optional[str] = None,
) -> str:
    """The app file a starter becomes for this app."""
    with open(build_relative_dir("templates", f"{starter}.py")) as file:
        source = file.read()
    keeps_version = APP_VERSION_PLACEHOLDER in source
    return render_template(
        source,
        render_app_arguments(
            identifier,
            version,
            author=author,
            scopes=scopes,
            logo=logo,
            version_variable=VERSION_VARIABLE if keeps_version else None,
        ),
        version=version,
    )


def create_command(
    ctx: typer.Context,
    path: Annotated[
        Optional[str],
        typer.Argument(
            help="The folder to create the app in. '.' is this folder. "
            "The default template asks for a name and makes a new folder of it."
        ),
    ] = None,
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
            help="What to set up. "
            + " ".join(f"'{name}': {t.summary}." for name, t in TEMPLATES.items())
            + " Each part can be changed with its own option.",
            callback=validate_project_template,
        ),
    ] = DEFAULT_TEMPLATE,
    starter: Annotated[
        Optional[str],
        typer.Option(
            "--starter",
            help="The code the app file starts with. Just a starting point, to be changed. Default: the template's ("
            + ", ".join(f"'{name}': {t.starter}" for name, t in TEMPLATES.items())
            + ").",
            callback=validate_starter,
        ),
    ] = None,
    ci: Annotated[
        Optional[Forge],
        typer.Option(
            "--ci",
            help="Release the app from this forge on every push, or 'none'. Default: the template's.",
        ),
    ] = None,
    flavour: Annotated[
        Optional[bool],
        typer.Option(
            "--flavour/--no-flavour",
            help="Write a flavour (a Dockerfile), so the app can be built into an image. Default: the template's.",
        ),
    ] = None,
    tests: Annotated[
        Optional[bool],
        typer.Option(
            "--tests/--no-tests",
            help="Write a first test of the app's actions (run with pytest). Default: the template's.",
        ),
    ] = None,
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
            help="The package manager to use. If uv is selected, it will initialize a project with uv. Default: the template's.",
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
    """Creates an Arkitekt app

    By default this makes a new folder holding everything an app needs to be
    developed and released: a uv project, an `app.py` that declares the app with
    `App(...)` (its identifier, version, author, scopes and logo; there is no
    separate manifest), tests of it, a flavour to build it into an image, and a
    GitHub workflow that releases it on every push: semantic-release reads the
    commits and raises the version.

    The app it starts with makes a random image and blurs one, storing both in
    mikro. `--starter simple` and `--starter filter` need no service.

    That is the `project` template. `--template blok` is the same project around
    a blok agent: it analyses images, keeps what it finds in a state, and declares
    a panel (a blok) the user interface draws from that state. `--template qt` makes a project for a desktop
    app instead: a window of its own (Qt) that others can call, and its tests, with
    no flavour and no workflow. `--template bare` writes only the app file,
    into this folder. Either way each part has its own option: `--package-manager`,
    `--flavour/--no-flavour`, `--tests/--no-tests`, `--ci`, `--starter`, and the
    folder itself.
    """
    from arkitekt.cli.commands.plugin.ci import CI_FILES, GITHUB_VISIBILITY_NOTE, write_ci
    from arkitekt.cli.commands.plugin.init import write_flavour

    console = get_console(ctx)
    parent_work_dir = get_work_dir(ctx)
    preset = TEMPLATES[template]

    if path is None:
        if not preset.new_folder:
            path = "."
        elif yes:
            cli_error(
                f"The '{template}' template creates the app in a new folder: name it "
                "(`arkitekt create my-app`), or pass `.` to use this one."
            )
        else:
            require_tty("`create`", hint="Name the folder: `arkitekt create my-app` (or `.` for this one).")
            path = str(typer.prompt("The name of your app (a new folder)"))

    # Resolve the target directory without changing process CWD. It is only named
    # here: nothing is made until every question is answered, so a wizard that is
    # left halfway, or refused, leaves no folder behind.
    work_dir = os.path.join(parent_work_dir, path) if path != "." else parent_work_dir

    # Each part is the option's when one was passed, and the template's otherwise.
    if package_manager is not None:
        manager = package_manager.value
    elif preset.package_manager is None or shutil.which(preset.package_manager):
        # Resolved at runtime (not at import) so detection respects the current env.
        manager = preset.package_manager or get_default_package_manager()
    else:
        manager = "pip"
        notice(
            console,
            f"{preset.package_manager} is not installed",
            "creating a plain app instead; install it and run `create` again for a project",
        )
    with_flavour = preset.flavour if flavour is None else flavour
    starter = preset.starter if starter is None else starter
    forge = preset.ci if ci is None else ci
    if forge is not Forge.none and manager != "uv":
        # What a forge runs is `uv run arkitekt plugin release`, on the project's lockfile.
        if ci is not None:
            cli_error(f"Releasing from {forge.value} needs a uv project. Pass --package-manager uv, or --ci none.")
        forge = Forge.none
    if forge is not Forge.none and not with_flavour:
        if ci is not None:
            cli_error(f"Releasing from {forge.value} builds a flavour, so --no-flavour leaves it nothing to release.")
        forge = Forge.none

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

    if manager == "uv" and not shutil.which("uv"):
        cli_error(
            "uv is not installed. Please install uv or choose another package manager."
        )

    entrypoint_file = os.path.join(work_dir, f"{entrypoint}.py")
    should_write_app = True
    if os.path.exists(entrypoint_file) and not overwrite_app and not yes:
        require_tty("`create`", hint=_CREATE_HINT)
        should_write_app = typer.confirm(
            "Entrypoint File already exists. Do you want to overwrite?"
        )

    # Every question is answered: from here on things are made.
    os.makedirs(work_dir, exist_ok=True)

    if manager == "uv":

        pyproject = os.path.join(work_dir, "pyproject.toml")
        if not os.path.exists(pyproject):
            had_repository = os.path.exists(os.path.join(work_dir, ".git"))
            subprocess.run(
                ["uv", "init", "--name", identifier, "--no-workspace"],
                check=True,
                cwd=work_dir,
            )
            if not had_repository and os.path.exists(os.path.join(work_dir, ".git")):
                start_on_default_branch(work_dir)
            needed = STARTER_EXTRAS.get(starter)
            if needed and with_extra and needs_extra(needed, with_extra):
                # The starter imports it: without it the app would not even load.
                with_extra = [*with_extra, needed]
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

    template_app = render_starter(starter, identifier, version, author=author, scopes=scopes, logo=logo)

    if should_write_app:
        with open(entrypoint_file, "w") as f:
            f.write(template_app)

    if with_flavour and not os.path.exists(os.path.join(work_dir, ".arkitekt", "flavours", "vanilla")):
        write_flavour(work_dir, "vanilla", template="uv" if manager == "uv" else "vanilla")

    test_file = None
    if preset.tests if tests is None else tests:
        test_file = write_tests(work_dir, starter, entrypoint)
        if test_file is None:
            notice(console, "tests/ already exists", "left as it is")
        elif manager == "uv":
            # What `uv run pytest` runs, here and in the release workflow.
            subprocess.run(["uv", "add", "--dev", "pytest"], check=True, cwd=work_dir)
            write_pytest_options(work_dir)

    workflow = None
    if forge is not Forge.none:
        if os.path.exists(os.path.join(work_dir, CI_FILES[forge.value])):
            notice(console, f"{escape(CI_FILES[forge.value])} already exists", "left as it is")
        else:
            workflow = write_ci(work_dir, forge.value, branch=current_branch(work_dir), entrypoint=entrypoint)

    if starter in STARTER_COMMANDS:
        command = STARTER_COMMANDS[starter].format(entrypoint=entrypoint)
        run_hint = f"uv run {command}" if manager == "uv" else command
    else:
        run_hint = (
            "arkitekt run dev" if entrypoint == "app" else f"arkitekt run dev {entrypoint}"
        )
    if path != ".":
        run_hint = f"cd {path} && {run_hint}"
    by = f" · {escape(author)}" if author else ""
    done(
        console,
        f"{escape(identifier)} {escape(version)}{by} was created in "
        f"{escape(os.path.join(path, os.path.basename(entrypoint_file)) if path != '.' else os.path.basename(entrypoint_file))}",
    )
    if test_file:
        runner = "uv run pytest" if manager == "uv" else "pytest"
        notice(console, f"{escape(test_file)} tests it", f"run them with `{runner}`")
        against_hub = hub_tests(work_dir, entrypoint)
        if against_hub:
            notice(
                console,
                f"{escape(against_hub)} tests it against a hub",
                f"run them with `{runner} -m hub` (needs Docker and konstruktor)",
            )
    if workflow:
        if forge is Forge.github:
            notice(
                console,
                f"{escape(workflow)} releases it on every push",
                "a `fix:` or `feat:` commit becomes the next version; semantic-release raises it for you",
            )
        else:
            notice(
                console,
                f"{escape(workflow)} releases it on every push",
                f"tag a commit v{escape(version)} to publish that version",
            )
        if forge is Forge.github:
            notice(console, "A package GitHub creates is private", GITHUB_VISIBILITY_NOTE)
    if starter in STARTER_NEEDS:
        what, how = STARTER_NEEDS[starter]
        notice(console, what, how.format(add="uv add" if manager == "uv" else "pip install"))
    notice(console, f"Start it with `{run_hint}`. We are excited to see what you come up with!")
