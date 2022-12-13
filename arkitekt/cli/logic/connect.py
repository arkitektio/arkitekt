import os
from rich import get_console
from rich.prompt import Confirm, Prompt
from .initialize import load_manifest, ensure_gitignore
import yaml
from typing import Dict
from fakts import Fakts
from fakts.grants.remote import DeviceCodeGrant
from fakts.discovery.base import FaktsEndpoint
from fakts.discovery.static import StaticDiscovery
import asyncio


available_scopes = [
    "arkitekt:rekuest:imitate",
    "arkitekt:herre",
    "arkitekt:fakts",
    "arkitekt:mikro:read",
    "arkitekt:mikro:imitate",
    "arkitekt:unlok",
]


def load_credentials(app_directory: str) -> Dict[str, str]:
    """Load the manifest from the app directory

    Args:
        app_directory (str): _description_

    Returns:
        [type]: _description_
    """
    config_path = os.path.join(app_directory, ".arkitekt")
    c_path = os.path.join(config_path, "credentials.yaml")

    with open(c_path, "r") as f:
        return yaml.safe_load(f)


def connect(
    app_directory: str,
    endpoint: str = None,
    refresh=None,
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
    manifest_path = os.path.join(config_path, "manifest.yaml")
    credentials_path = os.path.join(config_path, "credentials.yaml")

    initialize_fakts = True

    if not os.path.isfile(manifest_path):
        console.print("No manifest found. Please initialize the app first.")
        return

    console.print(f"Initializing a new Configuration")

    url = endpoint or (
        Prompt.ask(
            "Give us the path to your fakts instance",
            default=os.getenv("FAKTS_ENDPOINT_URL", "http://localhost:8000/f/"),
        )
        if not silent
        else os.getenv("FAKTS_ENDPOINT_URL", "http://localhost:8000/f/")
    )

    console.print("Connecting to fakts instance at " + url)

    manifest = load_manifest(app_directory)

    grant = DeviceCodeGrant(
        identifier=manifest.identifier,
        version=manifest.version,
        discovery=StaticDiscovery(base_url=url),
    )

    token = asyncio.run(grant.ademand(endpoint=FaktsEndpoint(base_url=url)))

    with open(credentials_path, "w") as f:
        yaml.safe_dump({url: token}, f)

    ensure_gitignore(app_directory)
