"""Shared helpers for the server-deployment CLI groups (`hub`, `coord`, `hubinator`,
`engine`).

Each group drives the migrated ``arkitekt_next.server`` library. The per-kind coupling
(name, config filename, config class, generator, wizard) lives in the single
:data:`arkitekt_next.server.deployments.DEPLOYMENTS` registry; the helpers here are the
generic ``init``/``up`` machinery parameterized by a :class:`DeploymentKind`:

- :func:`select_config`  -- wizard-or-default config selection (shared by hub/coord/hubinator)
- :func:`finalize`       -- apply an optional template, then write the profile YAML
- :func:`make_up_command`-- build the generic ``up`` command (identical across all kinds)

The registry transitively imports the ``server`` extra, so it is imported **only inside
function bodies** here (and the CLI callbacks), keeping the base CLI importable without
the extra.
"""

import importlib.util
import os
import shutil
from pathlib import Path
from typing import Annotated, Any, Callable, Optional, Type, TYPE_CHECKING

import typer
from pydantic import BaseModel

from arkitekt_next.cli.errors import cli_error
from arkitekt_next.cli.vars import get_console, get_work_dir

if TYPE_CHECKING:
    from arkitekt_next.server.deployments import DeploymentKind

#: Third-party deps that live in the optional ``server`` extra. Every one is
#: lazy-imported inside a server command callback, so the base CLI loads fine
#: without them; we only need them once a server subcommand actually runs. Names
#: are the import module names (``python-slugify`` imports as ``slugify``).
_SERVER_DEPS = ("cryptography", "inquirer", "ifaddr", "slugify", "dokker")


def require_server_deps() -> None:
    """Raise a friendly error if the ``server`` extra isn't installed.

    Call this at the top of a server command group's callback. Typer only runs the
    group callback when a subcommand is invoked (not for ``--help``), so help output
    stays dependency-free while e.g. ``hub init`` is guarded.
    """
    missing = [dep for dep in _SERVER_DEPS if importlib.util.find_spec(dep) is None]
    if missing:
        cli_error(
            "The server deployment stack needs extra dependencies "
            f"({', '.join(missing)}). Install them with:\n\n"
            "    pip install 'arkitekt-next[server]'"
        )


def resolve_path(ctx, path: str | None) -> Path:
    """Resolve the deployment directory: the positional ``path`` if given, else
    the global ``--work-dir``."""
    if path is None:
        return Path(get_work_dir(ctx))
    return Path(os.path.abspath(path))


def set_enabled_services(config, services) -> None:
    """Enable exactly ``services`` (an iterable of identifiers) and disable the rest.

    Only applies to profiles that carry data/compute service fields (hub /
    hubinator). ``lok`` is never toggled here.
    """
    from arkitekt_next.server.services import SERVICE_REGISTRY

    wanted = set(services)
    unknown = wanted - set(SERVICE_REGISTRY)
    if unknown:
        cli_error(
            f"Unknown service(s): {', '.join(sorted(unknown))}. "
            f"Available: {', '.join(sorted(SERVICE_REGISTRY))}"
        )
    for name in SERVICE_REGISTRY:
        if name == "lok" or not hasattr(config, name):
            continue
        getattr(config, name).enabled = name in wanted


def write_profile(
    ctx, path: Path, config: BaseModel, *, filename: str, kind: str, backend: str = "docker"
) -> Path:
    """Write ``config`` to ``<path>/<filename>`` under the versioned profile wrapper."""
    from arkitekt_next.server.utils import write_profile_yaml

    path.mkdir(parents=True, exist_ok=True)
    config_path = path / filename
    write_profile_yaml(str(config_path), config, kind=kind, backend=backend)
    get_console(ctx).print(
        f"[bold green]✓[/bold green] Wrote configuration to [cyan]{config_path}[/cyan]"
    )
    return config_path


def compose_and_up(
    ctx,
    path: Path,
    *,
    filename: str,
    model_cls: Type[BaseModel],
    generator: Callable[[Path, Any], None],
) -> None:
    """Load a profile config, regenerate the compose/config files, then ``docker compose up``."""
    from arkitekt_next.server.runner import compose_up
    from arkitekt_next.server.utils import load_profile_yaml

    console = get_console(ctx)
    config_path = path / filename
    try:
        config, _backend = load_profile_yaml(str(config_path), model_cls)
    except FileNotFoundError:
        cli_error(
            f"No configuration found at {config_path}. Run the matching `init` command first."
        )

    console.print("[blue]Composing deployment (services + auth wiring)...[/blue]")
    generator(path, config)

    # Docker is only required for `up` — generation above already succeeded, so if
    # Docker is missing we point the user at the ready-to-run files instead of failing
    # opaquely.
    if not shutil.which("docker"):
        cli_error(
            "Docker is not installed, but it is required to start the stack with `up`.\n"
            "The deployment files were generated in "
            f"{path} — install Docker (https://docs.docker.com/get-docker/) and run "
            "`docker compose up` there, or re-run this command."
        )

    console.print("[blue]Starting the stack with `docker compose up`...[/blue]")
    try:
        compose_up(path)
    except Exception as e:  # pragma: no cover - surfaced to the user
        cli_error(
            f"Failed to start the stack (is Docker running?): {e}"
        )
    console.print("[bold green]✓ Deployment is up.[/bold green]")


def select_config(
    spec: "DeploymentKind", console, *, wizard: bool, template: str | None, use_default: bool
) -> Any:
    """Pick the starting config: run the interactive wizard, or a bare default.

    The wizard runs when explicitly requested (``--wizard``) or when no template was
    given, unless ``--default`` was passed. This one formula is correct for all three
    wizard kinds: ``hubinator`` looks like it uses a simpler rule only because its
    ``--template`` defaults to ``"default"`` (never ``None``), which collapses this to
    ``wizard and not use_default``.
    """
    run_wizard = (wizard or template is None) and not use_default
    if run_wizard:
        if spec.wizard is None:  # defensive: only engine has no wizard, and it never calls this
            cli_error(f"The {spec.name} deployment has no interactive wizard.")
        return spec.wizard(console)
    return spec.config_cls()


def finalize(
    ctx, target: Path, config: BaseModel, spec: "DeploymentKind", *, template: str | None, backend: str
) -> Path:
    """Apply an optional template, then write the profile YAML for ``spec``."""
    if template is not None:
        from arkitekt_next.server.templates import apply_template

        config = apply_template(config, template)
    return write_profile(ctx, target, config, filename=spec.filename, kind=spec.name, backend=backend)


def make_up_command(kind_name: str) -> Callable[..., None]:
    """Build the generic ``up`` command function for a deployment kind.

    Identical across all kinds: load the profile, regenerate the compose/config files,
    then ``docker compose up``. The per-kind (filename, config class, generator) is
    resolved lazily from the registry inside the body so this factory stays free of
    the ``server`` extra at import time. The returned function has no decorator; the
    group ``main.py`` registers it via ``<group>_app.command("up")(make_up_command(...))``.
    """

    def up(
        ctx: typer.Context,
        path: Annotated[Optional[str], typer.Argument()] = None,
    ) -> None:
        """Compose the deployment (services + auth wiring) and run `docker compose up`."""
        from arkitekt_next.server.deployments import DEPLOYMENTS

        spec = DEPLOYMENTS[kind_name]
        compose_and_up(
            ctx,
            resolve_path(ctx, path),
            filename=spec.filename,
            model_cls=spec.config_cls,
            generator=spec.generator,
        )

    return up
