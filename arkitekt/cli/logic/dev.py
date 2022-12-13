import os
from rich import get_console
from rich.prompt import Confirm, Prompt
from .initialize import load_manifest, ensure_gitignore
from .connect import load_credentials
from arkitekt.cli.dev.autostage import watch_directory_and_stage
import asyncio


def dev(path, silent=False, token=None, endpoint=None):
    """Run the app

    Args:
        app_directory (str): _description_
        silent (bool, optional): _description_. Defaults to False.
    """
    if path == ".":
        app_directory = os.getcwd()
    else:
        app_directory = os.path.join(os.getcwd(), path)

    console = get_console()
    config_path = os.path.join(app_directory, ".arkitekt")
    manifest_path = os.path.join(config_path, "manifest.yaml")
    credentials_path = os.path.join(config_path, "credentials.yaml")

    initialize_fakts = True

    if not os.path.isfile(manifest_path):
        console.print("No manifest found. Please initialize the app first.")
        return

    if not os.path.isfile(credentials_path):
        console.print("No credentials found. Please connect the app first.")
        return

    if not silent:
        console.print(f"Loading manifest")

    if not token or not endpoint:
        credentials = load_credentials(app_directory)
        endpoint, token = next(iter(credentials.items()))

    asyncio.run(watch_directory_and_stage(path, token=token, endpoint=endpoint))
