from rich.console import Group
from rich.tree import Tree
from rich.panel import Panel
from arkitekt.app import App
from typing import MutableSet, Tuple, Any, Dict
import os
from .texts import LOGO, WELCOME_MESSAGE

def construct_codegen_welcome_panel() -> Panel:
    md = Panel(
        LOGO
        + "[white]"
        + WELCOME_MESSAGE
        + "\n\n"
        + "[bold green]Let's setup your codegen environment",
        title="Welcome to Arkitekt Codegen",
        title_align="center",
        border_style="green",
        style="green",
    )
    return md


def construct_changes_group(changes: MutableSet[Tuple[Any, str]]) -> Group:
    """Construct a rich panel group for the detected changes

    This panel is displayed if the app has detected changes before
    running the app. This can be caused by a change in the code or
    a change in the environment (e.g. a new package was installed)"""
    panel_header = "Detected changes\n"

    actor_tree = Tree("Changes in", style="white not bold")
    panel_group = Group(panel_header, actor_tree)
    for change, path in changes:
        actor_tree.add(os.path.normpath(path))

    return panel_group


def construct_app_group(app: App[Any]) -> Group:
    """Construct a rich panel group for the app

    It displays the app's identity and what it declares, read off the App itself:
    the App is the only place the identity lives.

    Parameters
    ----------
    app : App
        The app to construct the panel for

    Returns
    -------
    Group
        A rich panel group
    """
    by = f" by {app.author}" if app.author else ""
    panel_header = f"Running App \n\n{app.identifier}:{app.version}{by}\n"

    actor_tree = Tree("Registered Definitions", style="white not bold")
    service_tree = Tree("Depends on services", style="white not bold")

    # Rendered from the declaration, not a snapshot: a declaration the run will
    # reject is the run's error to report, not the panel's.
    for key in app.services:
        service_tree.add(key)

    if "rekuest" not in app.services:
        return Group(panel_header, service_tree)

    default = app.registry.get_implementations()

    for template in default:
        name = template.definition.name
        actor_tree.add(f"{template.interface}-{name}" if template.interface else name)

    panel_group = Group(panel_header, service_tree, actor_tree)

    return panel_group


def construct_leaking_group(variables: Dict[str, Any]) -> Group:
    """Construct a rich panel group for the leaking variables

    This panel is displayed if the app has leaking variables
    and is therefore considered to be not safe to run
    as an Arkitekt plugin

    Parameters
    ----------
    variables : Dict[str, Any]
        The leaking variables

    Returns
    -------
    Group
        The rich panel group
    """
    panel_header = (
        "Detected leaking Variables\n\n"
        "[white]Your app is leaking variables. "
        "Leaking variables can cause memory leaks and other issues."
        "Please make sure you are not defining variables in the"
        "global scope (outside of functions). "
        "If you want to define constants please make them all UPPERCASE\n\n"
    )

    actor_tree = Tree("Leaking Variables", style="white not bold")
    panel_group = Group(panel_header, actor_tree)
    for key, value in variables.items():
        actor_tree.add("key: " + key + " value: " + str(value))

    return panel_group


def construct_run_panel(app: App[Any]) -> Panel:
    app_group = construct_app_group(app)

    return Panel(
        app_group, style="bold green", border_style="green", title="Arkitekt Run"
    )
