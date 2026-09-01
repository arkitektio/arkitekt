"""Build the deployment command groups from the ``DEPLOYMENTS`` registry.

The four deployment kinds (`hub`, `coord`, `hubinator`, `engine`) used to live in
four near-identical ``main.py`` modules that differed only by a registry lookup.
They are now generated here: one Typer per registry entry, each carrying the same
lifecycle verbs plus its own ``init``.

The groups stay **top-level** (`arkitekt-next hub`, `arkitekt-next coord`, ...), so
command paths are unchanged.

Import discipline: ``server.deployments`` binds real config classes and generators
and therefore transitively imports the optional ``server`` extra, so it must never
be imported at module scope. The static metadata it needs here (names, help text,
``bootable``) lives in the dependency-free :mod:`arkitekt_next.server.kinds`, which
is safe to import eagerly. The group callback then enforces the extra at run time.
"""

import typer

from arkitekt_next.cli.commands._server_common import require_server_deps
from arkitekt_next.cli.commands.deployments.commands import (
    make_down_command,
    make_logs_command,
    make_status_command,
    make_up_command,
)
from arkitekt_next.cli.commands.deployments.connect import connect
from arkitekt_next.cli.commands.deployments.inits import INITS
from arkitekt_next.server.kinds import KINDS

#: Extra per-kind commands beyond the shared lifecycle + init.
EXTRA_COMMANDS = {"hub": {"connect": connect}}


def build_group(kind: str) -> typer.Typer:
    """Build one deployment kind's Typer group from its registry metadata."""
    meta = KINDS[kind]
    group = typer.Typer(no_args_is_help=True, help=meta.help)

    @group.callback()
    def _root(ctx: typer.Context) -> None:
        # Typer only runs a group callback when a subcommand is actually invoked
        # (not for --help), so help output stays dependency-free.
        require_server_deps()

    group.command("init")(INITS[kind])
    group.command("up")(make_up_command(kind))
    group.command("down")(make_down_command(kind))
    group.command("logs")(make_logs_command(kind))
    # An engine deploys no gateway, so there is no `/<service>/ht` for `status` to
    # probe -- `logs` is how you watch it.
    if meta.bootable:
        group.command("status")(make_status_command(kind))

    for name, command in EXTRA_COMMANDS.get(kind, {}).items():
        group.command(name)(command)

    return group


#: Every deployment group, keyed by the CLI name it is mounted under.
GROUPS = {kind: build_group(kind) for kind in KINDS}

# Named exports, so `cli/main.py` reads the same as before.
hub = GROUPS["hub"]
coord = GROUPS["coord"]
hubinator = GROUPS["hubinator"]
engine = GROUPS["engine"]
