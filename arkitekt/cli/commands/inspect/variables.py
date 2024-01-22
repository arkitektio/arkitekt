from importlib import import_module
import inspect as pyinspect
import rich_click as click

from arkitekt.cli.ui import construct_leaking_group
from arkitekt.cli.vars import get_console, get_manifest
from rich.panel import Panel

import rich_click as click


def inspect_dangerous_variables(module_path):
    """Inspect the module and return a dictionary of all the variables that are
    not upper case and that are not classes, modules, functions or builtins.

    This is used to check if a module is safe to import. Or if it runs code
    that might be dangegours:

    TODO: This is not the ebst way to do this. We should probably use the ast
    module to parse the module and check for dangerous code. This is a quick
    and dirty solution.

    """

    module = import_module(module_path)

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


def scan_module(module_path):
    """Scan a module for dangerous variables."""
    return inspect_dangerous_variables(module_path)


@click.command()
@click.pass_context
def variables(ctx, entrypoint):
    """Scans your arkitekt app for unsafe variables

    When designing an Arkitekt app, you should not have variables in your
    global scope, as on potential reloads (like for example in development)
    these variables will be redefined and cause memory leaks and other issues.

    You can use this command to scan your app for dangerous variables. If you
    have any, you should consider moving them into a function or class.

    """

    console = get_console(ctx)

    if not entrypoint:
        manifest = get_manifest(ctx)
        entrypoint = manifest.entrypoint

    variables = scan_module(entrypoint)

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
