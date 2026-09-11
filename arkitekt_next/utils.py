import os
import json
from typing import Optional


def create_arkitekt_next_folder(with_cache: bool = True, base_dir: Optional[str] = None) -> str:
    """Creates the .arkitekt_next folder in the given directory (defaults to cwd).

    If the folder already exists, it does nothing.
    It automatically creates a .gitignore file, and a .dockerignore file,
    so that the ArkitektNext credential files are not added to git.

    Parameters
    ----------
    with_cache : bool, optional
        Should we create a cache dir?, by default True
    base_dir : str, optional
        Base directory to create the folder in. Defaults to os.getcwd().

    Returns
    -------
    str
        The path to the .arkitekt_next folder.
    """
    root = base_dir or os.getcwd()
    folder = os.path.join(root, ".arkitekt_next")
    os.makedirs(folder, exist_ok=True)
    if with_cache:
        os.makedirs(os.path.join(folder, "cache"), exist_ok=True)

    gitignore = os.path.join(folder, ".gitignore")
    dockerignore = os.path.join(folder, ".dockerignore")
    if not os.path.exists(gitignore):
        with open(gitignore, "w") as f:
            f.write(
                "# Hiding ArkitektNext Credential files from git\n*.json\n*.temp\ncache/\nservers/"
            )
    if not os.path.exists(dockerignore):
        with open(dockerignore, "w") as f:
            f.write(
                "# Hiding ArkitektNext Credential files from git\n*.json\n*.temp\ncache/\nservers/"
            )

    return os.path.abspath(folder)


from typing import Any

def create_devcontainer_file(
    manifest: Any,
    flavour: str,
    docker_file_path: str,
    devcontainer_path: str = ".devcontainer",
) -> None:
    """Creates a devcontainer.json file that matches the docker file
    inside the flavour folder.

    It also adds the python extension and the arkitekt extension to the
    devcontainer.

    Parameters
    ----------
    flavour_folder : str
        The path to the flavour folder.
    """

    os.makedirs(devcontainer_path, exist_ok=True)

    flavour_container = os.path.join(devcontainer_path, flavour)
    os.makedirs(flavour_container, exist_ok=True)

    devcontainer_file = os.path.join(flavour_container, "devcontainer.json")

    devcontainer_content = {}
    devcontainer_content["name"] = f"{manifest.identifier} {flavour} Devcontainer"
    devcontainer_content["build"] = {}
    devcontainer_content["build"]["dockerfile"] = os.path.relpath(
        docker_file_path, flavour_container
    )
    devcontainer_content["build"]["context"] = (
        "../.."  # This is the root of the project
    )
    devcontainer_content["runArgs"] = ["--network=host"]
    devcontainer_content["customizations"] = {
        "vscode": {
            "extensions": [
                "ms-python.python",
                "ms-python.vscode-pylance",
                "jhnnsrs.arkitekt-next",
            ]
        }
    }

    with open(devcontainer_file, "w") as f:
        json.dump(devcontainer_content, f, indent=4)
