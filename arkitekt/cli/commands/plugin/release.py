"""``arkitekt plugin release``: test, build, inspect and publish an app, in one run.

This is the whole of what a CI job does for an app, and it asks nothing of the forge
it runs on beyond a checkout and a ``docker login``: what is being released is read
from git, and everything is published to one OCI repository.

The order is what makes a release trustworthy:

1. the repository's own tests run, before anything is built;
2. every flavour is built once, for all of its platforms, and pushed;
3. the pushed image is run, by digest, and says what it declares and who it is;
4. the release descriptor (:mod:`arkitekt_spec.release`) is pushed last.

So the image a release names is the image that was inspected, and a release exists
only once every step before its descriptor went through.
"""

import datetime
import os
import shlex
import subprocess
from dataclasses import dataclass
from typing import TYPE_CHECKING, Annotated, Any, Optional

import typer
from arkitekt_spec import AppManifest, Inspection, ReleaseDescriptor, ReleaseFlavour
from arkitekt_spec.release import channel_tag, channel_version, image_tag, release_tag

from arkitekt.app.app import VERSION_ENV
from arkitekt.cli.errors import cli_error
from arkitekt.cli.target import DEFAULT_TARGET, TargetArgument, load_app_or_exit
from arkitekt.cli.ui import done, escape, notice, step
from arkitekt.cli.vars import get_console, get_work_dir

from .build import (
    INSPECTION_TIMEOUT_SECONDS,
    InspectionError,
    flavour_relative_dir,
    inspect_docker_container,
    machine_readable,
)
from .registry import Repository, RegistryError

if TYPE_CHECKING:
    from .types import Flavour


@dataclass(frozen=True)
class Resolved:
    """What a run is about to release, as git says it."""

    version: str
    channel: Optional[str]
    revision: str
    source: Optional[str]

    @property
    def tag(self) -> str:
        """The tag the descriptor is pushed under."""
        return channel_tag(self.channel) if self.channel else release_tag(self.version)


def _git(work_dir: str, *arguments: str) -> Optional[str]:
    """The output of a git command, or None when it fails (or there is no git)."""
    try:
        result = subprocess.run(
            ["git", *arguments],
            cwd=work_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=False,
        )
    except OSError:
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def _source(work_dir: str) -> Optional[str]:
    """Where the source lives, without whatever credentials the remote url carries."""
    url = _git(work_dir, "remote", "get-url", "origin")
    if not url:
        return None
    scheme, separator, rest = url.partition("://")
    if separator and "@" in rest.split("/", 1)[0]:
        return f"{scheme}://{rest.split('@', 1)[1]}"
    return url


def resolve(
    declared_version: str, work_dir: str, channel: Optional[str] = None, allow_dirty: bool = False
) -> Resolved:
    """Decide what this checkout releases.

    A commit carrying the tag of the version the app declares is that release. Any
    other commit is a build of its branch's channel, versioned after the release it
    follows and the commit it is.

    Args:
        declared_version: The version the app declares in its source.
        work_dir: The checkout.
        channel: Build this channel, whatever git says. A forge that checks out a
            detached commit passes the branch name here.
        allow_dirty: Release even though the work tree has uncommitted changes.
    """
    revision = _git(work_dir, "rev-parse", "HEAD")
    if revision is None:
        cli_error(
            "A release is made from a git commit, and this folder is not in a git "
            "repository (or has no commit yet)."
        )
    if not allow_dirty and _git(work_dir, "status", "--porcelain", "--untracked-files=no"):
        cli_error(
            "The work tree has uncommitted changes, so the commit a release names would not "
            "be what was built. Commit them, or pass --allow-dirty."
        )
    source = _source(work_dir)

    if channel is None:
        tags = (_git(work_dir, "tag", "--points-at", "HEAD") or "").split()
        if declared_version in [tag.removeprefix("v") for tag in tags]:
            return Resolved(declared_version, None, revision, source)
        versions = [tag for tag in tags if tag.removeprefix("v")[:1].isdigit()]
        if versions:
            cli_error(
                f"This commit is tagged {', '.join(versions)}, but the app declares version "
                f"{declared_version}. A release is the commit whose tag is its app's version: "
                "set the version in the app, commit, and tag that commit."
            )
        channel = _git(work_dir, "symbolic-ref", "--short", "HEAD")
        if channel is None:
            cli_error(
                "This is a detached commit without a version tag, so git cannot say which "
                "branch it is a build of. Pass --channel (CI knows the branch name)."
            )

    return Resolved(channel_version(declared_version, revision), channel, revision, source)


def default_test_command(work_dir: str) -> Optional[list[str]]:
    """The tests a repository has, when it does not say how to run them."""
    if not os.path.isdir(os.path.join(work_dir, "tests")):
        return None
    if os.path.exists(os.path.join(work_dir, "uv.lock")):
        return ["uv", "run", "pytest"]
    return ["python", "-m", "pytest"]


def push_flavour(
    name: str,
    flavour: "Flavour",
    reference: str,
    resolved: Resolved,
    work_dir: str,
    platforms: list[str],
    console: Any,
) -> None:
    """Build a flavour for all of its platforms and push it, as one image."""
    from .buildx import ensure_builder

    relative_dir = flavour_relative_dir(name)

    if flavour.is_customized():
        # Run as written. Such a command has no place for the platform list or a
        # build argument, so it yields this machine's image and the source's version.
        commands = [flavour.generate_build_command(reference, relative_dir), ["docker", "push", reference]]
    else:
        extra = ["--build-arg", f"{VERSION_ENV}={resolved.version}"] if resolved.channel else []
        commands = [
            flavour.generate_build_command(
                reference,
                relative_dir,
                platform=",".join(platforms),
                output="--push",
                builder=ensure_builder(platforms, console=console),
                extra=extra,
            )
        ]

    for command in commands:
        if subprocess.run(command, cwd=work_dir).returncode != 0:
            cli_error(f"Could not build and push flavour {name} (`{' '.join(command)}` failed)")


def inspect_image(
    image: str, target: str, platform: Optional[str] = None
) -> tuple[Inspection, Optional[AppManifest]]:
    """Run a pushed image and read what it declares, and who it says it is.

    The image is pulled by its digest, so this runs what the registry holds rather
    than what the build left behind. An image whose arkitekt predates
    ``plugin release`` reports no manifest; the caller decides whether that matters.
    """
    command = ["docker", "run", "--rm", "--pull", "always", "--network", "host"]
    if platform:
        command += ["--platform", platform]
    command += [image, "arkitekt", "inspect", "all", target, "-mr"]
    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=INSPECTION_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired:
        cli_error(
            f"Inspecting {image} timed out after {INSPECTION_TIMEOUT_SECONDS}s. Make sure "
            "`arkitekt inspect all` returns inside the image."
        )

    try:
        runtime = machine_readable(result.stdout, "AGENT")
        manifest = machine_readable(result.stdout, "MANIFEST")
        if result.returncode != 0 or runtime is None:
            cli_error(
                f"Running `arkitekt inspect all {target}` inside {image} failed:\n{result.stdout}"
            )
        size, _ = inspect_docker_container(image)
    except InspectionError as error:
        cli_error(str(error))

    return (
        Inspection.model_validate({**runtime, "size": size}),
        AppManifest.model_validate(manifest) if manifest is not None else None,
    )


def check_identity(
    name: str, reported: Optional[AppManifest], manifest: AppManifest, resolved: Resolved
) -> None:
    """Refuse an image that would register as something else than the release says.

    A deployer admits a container by the identifier and version it registers with,
    so a descriptor that names another version describes an image nobody can run.
    """
    if reported is None:
        if resolved.channel is None:
            return  # An older arkitekt: it carries the source's version, which is the release's.
        cli_error(
            f"The image of flavour {name} does not say which version it is, and a build of "
            f"the '{resolved.channel}' channel has to carry {resolved.version}. Its arkitekt "
            "predates channel builds: update the arkitekt the image installs."
        )
    if reported.identifier != manifest.identifier:
        cli_error(
            f"The image of flavour {name} holds the app '{reported.identifier}', "
            f"not '{manifest.identifier}'."
        )
    if reported.version != resolved.version:
        cli_error(
            f"The image of flavour {name} is version {reported.version}, but this is a build "
            f"of {resolved.version}. Its Dockerfile has to take the version of the build:\n"
            f'    ARG {VERSION_ENV}=""\n'
            f"    ENV {VERSION_ENV}=${VERSION_ENV}\n"
            "(a flavour with its own build_command is never passed it)."
        )


def offered(inspection: Inspection) -> list[str]:
    """The interfaces an image offers, for comparing two platforms of one flavour."""
    return sorted(implementation.interface or "" for implementation in inspection.implementations)


def release(
    ctx: typer.Context,
    target: TargetArgument = DEFAULT_TARGET,
    repository: Annotated[
        Optional[str],
        typer.Option(
            "--repository",
            "-r",
            envvar="ARKITEKT_REPOSITORY",
            help="The OCI repository to publish to, e.g. ghcr.io/you/your-app. "
            "It is what others import to install the app.",
        ),
    ] = None,
    channel: Annotated[
        Optional[str],
        typer.Option(
            "--channel",
            envvar="ARKITEKT_CHANNEL",
            help="Build this channel instead of asking git for the branch.",
        ),
    ] = None,
    test_command: Annotated[
        Optional[str],
        typer.Option(
            "--test-command", help="How to run the app's tests. Default: pytest, if there is a tests folder."
        ),
    ] = None,
    no_test: Annotated[bool, typer.Option("--no-test", help="Do not run the app's tests.")] = False,
    platform: Annotated[
        Optional[list[str]],
        typer.Option(
            "--platform",
            "-p",
            help="Build for these platforms instead of the ones each flavour declares. Repeatable.",
        ),
    ] = None,
    inspect_all_platforms: Annotated[
        bool,
        typer.Option(
            "--inspect-all-platforms",
            help="Run the image of every platform (under emulation), not only this machine's.",
        ),
    ] = False,
    allow_dirty: Annotated[
        bool, typer.Option("--allow-dirty", help="Release with uncommitted changes.")
    ] = False,
) -> None:
    """Test, build and publish the app: what a CI job runs.

    A commit tagged with the app's version becomes that release, which never changes
    afterwards. Any other commit becomes the latest build of its branch's channel.
    """
    from .buildx import host_platform
    from .io import app_to_manifest, get_flavours

    console = get_console(ctx)
    work_dir = get_work_dir(ctx)

    if not repository:
        cli_error("Name the repository to publish to: --repository ghcr.io/you/your-app.")
    try:
        registry = Repository.of(repository)
    except ValueError as error:
        cli_error(str(error))

    app = load_app_or_exit(ctx, target)
    declared = app_to_manifest(app, target)
    flavours = get_flavours(base_dir=work_dir)
    if not flavours:
        cli_error("There is no flavour to release. Run `arkitekt plugin init` first.")

    try:
        resolved = resolve(declared.version, work_dir, channel=channel, allow_dirty=allow_dirty)
        tags = {name: image_tag(resolved.version, name) for name in flavours}
        descriptor_tag = resolved.tag
    except ValueError as error:
        cli_error(str(error))
    manifest = declared.model_copy(update={"version": resolved.version})

    step(
        console,
        f"Releasing [bold]{escape(manifest.identifier)}[/bold] {escape(resolved.version)}",
        escape(f"channel {resolved.channel}" if resolved.channel else "release")
        + f" · {escape(registry.name)}",
    )

    try:
        if resolved.channel is None and registry.has(descriptor_tag):
            cli_error(
                f"{registry.name}:{descriptor_tag} is already released, and a release never "
                "changes. Raise the app's version and tag the new commit."
            )
    except RegistryError as error:
        # A repository nothing was pushed to yet is answered with a refusal by some
        # registries, not with "not found". If the login is what is wrong, the push says so.
        if error.status not in (401, 403):
            cli_error(str(error))

    if not no_test:
        tests = shlex.split(test_command) if test_command else default_test_command(work_dir)
        if tests is None:
            notice(console, "No tests to run", "there is no tests folder; pass --test-command")
        else:
            step(console, "Running the tests", escape(" ".join(tests)))
            if subprocess.run(tests, cwd=work_dir).returncode != 0:
                cli_error("The tests failed, so nothing was built or published.")

    host = host_platform()
    released: list[ReleaseFlavour] = []
    for name, flavour in flavours.items():
        platforms = [host] if flavour.is_customized() else list(platform or flavour.platforms)
        reference = f"{registry.name}:{tags[name]}"

        step(console, f"Building flavour [bold]{escape(name)}[/bold]", escape(", ".join(platforms)))
        push_flavour(name, flavour, reference, resolved, work_dir, platforms, console)

        try:
            pushed = registry.manifest_digest(tags[name])
        except RegistryError as error:
            cli_error(str(error))
        if pushed is None:
            cli_error(f"{reference} was pushed, but the registry does not have it.")
        image = registry.pinned(pushed)

        step(console, f"Inspecting flavour [bold]{escape(name)}[/bold]", escape(image))
        inspection, reported = inspect_image(image, declared.entrypoint)
        check_identity(name, reported, manifest, resolved)

        if inspect_all_platforms:
            for other in platforms:
                if other == host:
                    continue
                step(console, f"Inspecting flavour [bold]{escape(name)}[/bold]", escape(other))
                elsewhere, _ = inspect_image(image, declared.entrypoint, platform=other)
                if offered(elsewhere) != offered(inspection):
                    cli_error(
                        f"Flavour {name} offers {offered(elsewhere)} on {other} but "
                        f"{offered(inspection)} on {host}. A flavour is one app on every platform."
                    )

        released.append(
            ReleaseFlavour(
                name=name,
                description=flavour.description or None,
                image=image,
                platforms=platforms,
                selectors=flavour.selectors,
                inspection=inspection,
                built_at=datetime.datetime.now(datetime.timezone.utc),
            )
        )

    descriptor = ReleaseDescriptor(
        manifest=manifest,
        channel=resolved.channel,
        revision=resolved.revision,
        source=resolved.source,
        flavours=released,
    )
    try:
        registry.push_release(descriptor_tag, descriptor)
    except RegistryError as error:
        cli_error(str(error))

    done(
        console,
        f"Released [bold]{escape(manifest.identifier)}[/bold] {escape(resolved.version)}",
        escape(f"{registry.name}:{descriptor_tag}"),
    )
    notice(console, "Install it by importing the repository", escape(registry.name))
