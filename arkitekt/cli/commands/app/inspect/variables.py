import inspect as pyinspect
import json
from typing import Annotated

import typer

from arkitekt.cli.ui import construct_leaking_group
from arkitekt.cli.utils import emit_machine_readable
from arkitekt.cli.target import DEFAULT_TARGET, TargetArgument, import_target_or_exit
from arkitekt.cli.vars import get_console
from rich.panel import Panel


def inspect_dangerous_variables(module):
    """Inspect the module and return a dictionary of all the variables that are
    not upper case and that are not classes, modules, functions or builtins.

    This is used to check if a module is safe to import. Or if it runs code
    that might be dangegours:

    TODO: This is not the ebst way to do this. We should probably use the ast
    module to parse the module and check for dangerous code. This is a quick
    and dirty solution.

    """

    dangerous_variables = {}

    for key, value in pyinspect.getmembers(module):
        if key.startswith("_"):
            continue
        if pyinspect.isclass(value):
            continue
        if pyinspect.ismodule(value):
            continue
        if pyinspect.isfunction(value):
            continue
        if pyinspect.isbuiltin(value):
            continue

        if type(value) in [str, float, int, bool, list, dict, tuple]:
            if key != key.upper():
                dangerous_variables[key] = value
            continue

    return dangerous_variables


def scan_module(module):
    """Scan a module for dangerous variables."""
    return inspect_dangerous_variables(module)


def variables(
    ctx: typer.Context,
    target: TargetArgument = DEFAULT_TARGET,
    pretty: Annotated[
        bool,
        typer.Option("--pretty", "-p", help="Should we just output json?"),
    ] = False,
    machine_readable: Annotated[
        bool,
        typer.Option("--machine-readable", "-mr", help="Should we just output json?"),
    ] = False,
):
    """Scans your arkitekt app for unsafe variables

    When designing an Arkitekt app, you should not have variables in your
    global scope, as on potential reloads (like for example in development)
    these variables will be redefined and cause memory leaks and other issues.

    You can use this command to scan your app for dangerous variables. If you
    have any, you should consider moving them into a function or class.

    """

    console = get_console(ctx)
    # Only the module is scanned, so it need not declare an app.
    module, _ = import_target_or_exit(ctx, target)

    variables = scan_module(module)

    # The values can be arbitrary objects; stringify anything JSON can't carry.
    serializable = {key: repr(value) for key, value in variables.items()}

    if machine_readable:
        emit_machine_readable("VARIABLES", serializable)
        return
    if pretty:
        console.print(json.dumps(serializable, indent=2))
        return

    if not variables:
        console.print(
            Panel(
                "No dangerous variables found. You are good to go!  🎉",
                style="green",
                border_style="green",
                title="Arkitekt Scan",
            )
        )
        return

    group = construct_leaking_group(variables)

    panel = Panel(
        group, title="Arkitekt Scan", expand=True, border_style="red", style="red"
    )
    console.print(panel)
