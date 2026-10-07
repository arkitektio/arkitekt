"""``arkitekt plugin ci``: have a forge release the app on every push.

What a forge runs is ``arkitekt plugin release``; the files written here only call
it. They are the forge's part: where the job is declared and how it logs in.
"""

import os
from importlib import metadata

import typer

from arkitekt.cli.errors import cli_error
from arkitekt.cli.ui import done, escape, notice
from arkitekt.cli.vars import get_console, get_work_dir

ci = typer.Typer(no_args_is_help=True, help="Release the app from CI on every push.")

_GITHUB = """\
name: Release

# Every push to {branch} is tested and published. semantic-release reads the commits since
# the last release (https://www.conventionalcommits.org): if a `fix:` or a `feat:` is among
# them it raises the app's version in {module}.py, commits and tags that (v1.2.3), and the
# commit is published as that release. Any other push publishes the latest build of the
# {branch} channel.
on:
  push:
    branches: [{branch}]

# One release at a time: the next push waits for the version this one may commit.
concurrency: release-${{{{ github.ref }}}}

jobs:
  release:
    runs-on: ubuntu-latest
    permissions:
      # To push the version's commit and tag, and to create the GitHub release.
      contents: write
      packages: write
    steps:
      - uses: actions/checkout@v4
        with:
          # semantic-release reads the whole history, and its tags.
          fetch-depth: 0
      - uses: astral-sh/setup-uv@v6
      # Before a version is cut: a tag is not taken back when a test fails after it.
      - name: Test
        run: uv run pytest
      - name: Version
        id: version
        env:
          GH_TOKEN: ${{{{ github.token }}}}
        run: uvx --from "{semantic_release}" semantic-release version
      - uses: arkitektio/arkitekt/ci/github@{ref}
        with:
          target: {module}
          # The commit semantic-release tagged is that release, not a build of the branch.
          release: ${{{{ steps.version.outputs.released }}}}
"""

#: The semantic-release the workflow runs. Its major is pinned: a new one may read
#: the configuration differently.
SEMANTIC_RELEASE = "python-semantic-release>=10,<11"

#: What tells semantic-release where the app's version is, and which branch releases.
#: Only the app file carries the version: raising one in pyproject.toml as well would
#: leave uv.lock behind, and a release is not made from a tree that changed.
_SEMANTIC_RELEASE = """
[tool.semantic_release]
version_variables = ["{module}.py:__version__"]
commit_message = "chore(release): {{version}} [skip ci]"
tag_format = "v{{version}}"
allow_zero_version = true

[tool.semantic_release.branches.release]
match = "{branch}"
prerelease = false
"""

_GITLAB = """\
include:
  - remote: https://raw.githubusercontent.com/arkitektio/arkitekt/{ref}/ci/gitlab/arkitekt.gitlab-ci.yml
"""


def _ref() -> str:
    """The arkitekt the workflow is pinned to: the release this CLI is, if it is one."""
    try:
        version = metadata.version("arkitekt")
    except metadata.PackageNotFoundError:
        return "main"
    return f"v{version}" if version.replace(".", "").isdigit() else "main"


#: Where each forge reads its configuration from, relative to the project.
CI_FILES = {
    "github": os.path.join(".github", "workflows", "release.yaml"),
    "gitlab": ".gitlab-ci.yml",
}


def render_ci(forge: str, branch: str = "main", entrypoint: str = "app") -> str:
    """The configuration that has a forge release the app on every push."""
    template = {"github": _GITHUB, "gitlab": _GITLAB}[forge]
    return template.format(branch=branch, ref=_ref(), module=entrypoint, semantic_release=SEMANTIC_RELEASE)


def render_semantic_release(branch: str = "main", entrypoint: str = "app") -> str:
    """What a project's ``pyproject.toml`` tells semantic-release."""
    return _SEMANTIC_RELEASE.format(branch=branch, module=entrypoint)


def write_semantic_release(work_dir: str, branch: str = "main", entrypoint: str = "app") -> bool:
    """Tell semantic-release where the app's version is, unless the project already does.

    Returns:
        Whether ``pyproject.toml`` was written to.
    """
    path = os.path.join(work_dir, "pyproject.toml")
    existing = ""
    if os.path.exists(path):
        with open(path) as file:
            existing = file.read()
    if "[tool.semantic_release" in existing:
        return False
    with open(path, "a") as file:
        file.write(render_semantic_release(branch, entrypoint))
    return True


def declares_version_variable(work_dir: str, entrypoint: str = "app") -> bool:
    """Whether the app file keeps its version where semantic-release can raise it."""
    try:
        with open(os.path.join(work_dir, f"{entrypoint}.py")) as file:
            return any(line.startswith("__version__") for line in file)
    except OSError:
        return False


def write_ci(
    work_dir: str, forge: str, branch: str = "main", overwrite: bool = False, entrypoint: str = "app"
) -> str:
    """Write a forge's release configuration into a project; return its relative path.

    Args:
        work_dir: The project.
        forge: ``github`` or ``gitlab``.
        branch: The branch whose pushes are published (GitHub only: GitLab
            publishes its default branch).
        overwrite: Replace a configuration that exists.
        entrypoint: The module the app is in (GitHub only: it is where
            semantic-release raises the version).
    """
    relative = CI_FILES[forge]
    path = os.path.join(work_dir, relative)
    if os.path.exists(path) and not overwrite:
        cli_error(f"{relative} already exists. Pass --overwrite to replace it.")
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as file:
        file.write(render_ci(forge, branch, entrypoint))
    if forge == "github":
        write_semantic_release(work_dir, branch, entrypoint)
    return relative


#: What a user has to do once, by hand, for a package GitHub creates.
GITHUB_VISIBILITY_NOTE = "make it public once, in its settings, so others can import it"


@ci.command("github")
def github(
    ctx: typer.Context,
    branch: str = typer.Option("main", help="The branch whose pushes are published."),
    entrypoint: str = typer.Option(
        "app", "--entrypoint", "-e", help="The python file the app is in, without the .py ending."
    ),
    overwrite: bool = typer.Option(False, "--overwrite", help="Replace an existing workflow."),
) -> None:
    """Write a GitHub Actions workflow that versions the app with semantic-release and publishes it to ghcr.io."""
    console = get_console(ctx)
    work_dir = get_work_dir(ctx)
    entrypoint = entrypoint.removesuffix(".py")
    relative = write_ci(work_dir, "github", branch=branch, overwrite=overwrite, entrypoint=entrypoint)
    done(console, f"Wrote [bold]{escape(relative)}[/bold]", "commit it to release on every push")
    notice(
        console,
        "semantic-release raises the version",
        "a `fix:` or `feat:` commit becomes the next one; it is configured in pyproject.toml",
    )
    if not declares_version_variable(work_dir, entrypoint):
        notice(
            console,
            f"{escape(entrypoint)}.py has no __version__",
            f'semantic-release raises that variable: write `__version__ = "1.2.3"` and declare the app with it, '
            f"`App({escape(repr('...'))}, __version__)`",
        )
    notice(console, "A package GitHub creates is private", GITHUB_VISIBILITY_NOTE)


@ci.command("gitlab")
def gitlab(
    ctx: typer.Context,
    overwrite: bool = typer.Option(False, "--overwrite", help="Replace an existing .gitlab-ci.yml."),
) -> None:
    """Write a GitLab CI configuration that publishes to the project's registry."""
    relative = write_ci(get_work_dir(ctx), "gitlab", overwrite=overwrite)
    done(get_console(ctx), f"Wrote [bold]{escape(relative)}[/bold]", "commit it to release on every push")
