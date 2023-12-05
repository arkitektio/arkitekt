from rich.console import Group
from rich.tree import Tree
from rich.panel import Panel
from arkitekt.apps import App
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


def construct_app_group(app: App) -> Group:
    """Construct a rich panel group for the app

    It displays the registered definitions

    Parameters
    ----------
    app : App
        The app to construct the panel for

    Returns
    -------
    Group
        A rich panel group
    """
    panel_header = f"Running App \n\n{app.manifest.identifier}:{app.manifest.version}\n"

    actor_tree = Tree("Registered Definitions", style="white not bold")
    panel_group = Group(panel_header, actor_tree)
    for key, definition in app.rekuest.agent.definition_registry.definitions.items():
        actor_tree.add(key)

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


def construct_run_panel(app: App) -> Panel:
    app_group = construct_app_group(app)

    return Panel(
        app_group, style="bold green", border_style="green", title="Arkitekt Run"
    )
