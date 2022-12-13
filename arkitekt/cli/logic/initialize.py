import os
from rich import get_console
from rich.prompt import Confirm, Prompt
import yaml
from pydantic import BaseModel
from typing import List, Optional

available_scopes = [
    "arkitekt:rekuest:imitate",
    "arkitekt:herre",
    "arkitekt:fakts",
    "arkitekt:mikro:read",
    "arkitekt:mikro:imitate",
    "arkitekt:unlok",
]


class SoftwareManifest(BaseModel):
    identifier: str
    version: str
    description: Optional[str]
    scopes: List[str]


def ensure_gitignore(app_directory: str):
    """Ensure that the .gitignore file is present

    Args:
        app_directory (str): _description_
    """
    config_path = os.path.join(app_directory, ".arkitekt")
    gitignore_path = os.path.join(config_path, ".gitignore")
    gitignore = """credentials.yaml"""
    with open(gitignore_path, "w") as f:
        f.write(gitignore)
    dockerignore_path = os.path.join(config_path, ".dockerignore")
    dockerignore = """credentials.yaml"""
    with open(dockerignore_path, "w") as f:
        f.write(dockerignore)


def load_manifest(app_directory: str) -> SoftwareManifest:
    """Load the manifest from the app directory

    Args:
        app_directory (str): _description_

    Returns:
        [type]: _description_
    """
    config_path = os.path.join(app_directory, ".arkitekt")
    fakts_path = os.path.join(config_path, "manifest.yaml")

    with open(fakts_path, "r") as f:
        return SoftwareManifest(**yaml.safe_load(f))


def initialize_manifest(
    app_directory: str,
    identifier: str = None,
    version: str = None,
    description: str = None,
    silent=False,
):
    """Initialize a new Arkitekt app



    Args:
        console (Console): _description_
        app_directory (str): _description_
        refresh (_type_, optional): _description_. Defaults to None.
        silent (bool, optional): _description_. Defaults to False.
    """

    # Create the project directory

    # Create the arkitekt.json file
    console = get_console()
    config_path = os.path.join(app_directory, ".arkitekt")
    if not os.path.exists(config_path):
        os.makedirs(config_path)

    fakts_path = os.path.join(config_path, "manifest.yaml")
    os.path.join(config_path, ".gitignore")

    initialize_fakts = True

    manifest = None

    if os.path.isfile(fakts_path):
        console.print(
            f"There seems to have been a previous app initialized at {app_directory}"
        )
        initialize_fakts = (
            Confirm.ask("Do you want to refresh the Apps configuration? ")
            if not silent
            else False
        )
        if not initialize_fakts:
            console.print(f"Nothing done. Bye :smiley: ")
            return

        with open(fakts_path, "r") as f:
            manifest = SoftwareManifest(**yaml.safe_load(f))

    console.print(f"Initializing a new Configuration")

    app_identifier = (
        identifier
        if identifier
        else Prompt.ask(
            "Give your app a unique identifier",
            default=manifest.identifier if manifest else None,
        )
    )
    app_version = (
        version
        if version
        else Prompt.ask(
            "Give your app a version", default=manifest.version if manifest else None
        )
    )
    app_description = (
        description
        if description
        else Prompt.ask(
            "Give your app a description",
            default=manifest.description if manifest else None,
        )
    )

    console.log("Which scopes do you want your app to have?")
    scopes = []
    for scope in available_scopes:
        if Confirm.ask(
            f"App should have {scope} scope?",
            default=scope in manifest.scopes if manifest else False,
        ):
            scopes.append(scope)

    if not scopes:
        console.print("App needs at least one scope")
        return

    manifest = {
        "identifier": app_identifier,
        "version": app_version,
        "description": app_description,
        "scopes": scopes,
    }

    with open(fakts_path, "w") as f:
        yaml.dump(manifest, f)

    ensure_gitignore(app_directory)
