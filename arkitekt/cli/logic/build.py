import os
from rich import get_console
from rich.prompt import Confirm, Prompt
from .initialize import load_manifest, ensure_gitignore
from .connect import load_credentials
import yaml
from fakts import Fakts
from fakts.grants.remote import DeviceCodeGrant
from fakts.discovery.base import FaktsEndpoint
from fakts.discovery.static import StaticDiscovery
from arkitekt.cli.prod.run import import_directory_and_start
import asyncio
import subprocess
from typing import List
from pydantic import BaseModel
import pydantic


class BuildManifest(BaseModel):
    builder: str = "port"
    version: str
    identifier: str
    scopes: list
    image: str


class PortYaml(BaseModel):
    builds: List[BuildManifest]


def build(path, silent=False, tag=None):
    """Run the app

    Args:
        app_directory (str): _description_
        silent (bool, optional): _description_. Defaults to False.
    """
    if path == ".":
        app_directory = os.getcwd()
    else:
        app_directory = os.path.join(os.getcwd(), path)

    assert tag, "Please provide a tag"

    print(app_directory)
    dockerfile = os.path.join(app_directory, "Dockerfile")
    if not os.path.isfile(dockerfile):
        console = get_console()
        console.print("No Dockerfile found. Please create a Dockerfile first.")
        return

    manifest = load_manifest(app_directory)
    print(tag)

    x = subprocess.run(["docker", "build", "-t", tag, "."], cwd=app_directory)

    portyaml = os.path.join(app_directory, ".arkitekt/port.yaml")
    if os.path.isfile(portyaml):
        with open(portyaml, "w") as f:
            try:
                port = PortYaml(**yaml.safe_load(f))
            except Exception as e:
                console = get_console()
                console.print("Invalid port.yaml file. Overwriting")
                port = PortYaml(builds=[])
                return
    else:
        port = PortYaml(builds=[])

    port.builds.append(BuildManifest(**manifest.dict(), image=tag, builder="port"))

    with open(portyaml, "w") as f:
        yaml.safe_dump(port.dict(), f)
