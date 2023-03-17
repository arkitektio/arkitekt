from rich.console import Group
from rich.tree import Tree
from rich.panel import Panel
from arkitekt.apps import Arkitekt
from typing import MutableSet, Tuple, Any, Dict
import os


def construct_changes_group(changes: MutableSet[Tuple[Any,str]]) -> Group:
    panel_header = "Detected changes\n"

    actor_tree = Tree("Changes in", style="white not bold")
    panel_group = Group(
        panel_header,
        actor_tree
        
    )
    for change, path in changes:
        actor_tree.add(os.path.normpath(path))

    return panel_group



def construct_app_group(app: Arkitekt) -> Group:
    panel_header = f"Running App \n\n{app.identifier}:{app.version}\n"

    actor_tree = Tree("Registered Definitions", style="white not bold")
    panel_group = Group(
        panel_header,
        actor_tree
        
    )
    for definition in app.rekuest.definition_registry.definitions.keys():
        actor_tree.add(definition.interface)

    return panel_group


def construct_leaking_group(variables: Dict[str, Any]) -> Group:
    panel_header = "Detected leaking Variables\n\n"\
          "[white]Your app is leaking variables. "\
          "Leaking variables can cause memory leaks and other issues." \
            "Please make sure you are not defining variables in the"\
            "global scope (outside of functions). " \
                "If you want to define constants please make them all UPPERCASE\n\n"

    actor_tree = Tree("Leaking Variables", style="white not bold")
    panel_group = Group(
        panel_header,
        actor_tree
        
    )
    for key, value in variables.items():
        actor_tree.add("key: " + key + " value: " + str(value))

    return panel_group




def construct_run_panel(app: Arkitekt) -> Panel:

    app_group = construct_app_group(app)

    return Panel(app_group, style="bold green", border_style="green", title="Arkitekt Run")
