import os
import json
from typing import Optional

from fakts.cache.file import ensure_private_dir


def create_arkitekt_folder(with_cache: bool = False, base_dir: Optional[str] = None) -> str:
    """Creates the .arkitekt folder in the given directory (defaults to cwd).

    If the folder already exists, it does nothing.
    It automatically creates a .gitignore file, and a .dockerignore file,
    so that the Arkitekt credential files are not added to git.

    Parameters
    ----------
    with_cache : bool, optional
        Create an (empty) `cache/` subdirectory, by default False. The fakts
        session cache no longer lives here -- it moved to a private per-user
        directory, see `arkitekt.app.fakts._cache_path` -- so nothing writes
        into it any more. Kept only for callers that still expect the folder.
    base_dir : str, optional
        Base directory to create the folder in. Defaults to os.getcwd().

    Returns
    -------
    str
        The path to the .arkitekt folder.
    """
    root = base_dir or os.getcwd()
    folder = os.path.join(root, ".arkitekt")

    # 0700, not whatever the umask allows. This folder holds the fakts cache
    # -- a live, rotating refresh token -- plus `servers/` and the credential
    # JSONs the .gitignore written below exists to hide. A bare os.makedirs
    # yields 0775 under the umask 002 that Debian and Ubuntu ship, which is
    # what used to make fakts refuse to read its own cache and silently
    # re-run the device-code flow.
    ensure_private_dir(folder)
    if with_cache:
        ensure_private_dir(os.path.join(folder, "cache"))

    ensure_ignored(os.path.join(folder, ".gitignore"))
    ensure_ignored(os.path.join(folder, ".dockerignore"))

    return os.path.abspath(folder)


#: What the ``.arkitekt/`` folder hides: credentials, caches and the rekuest agent's
#: journal of unacknowledged frames (SQLite, with its ``-wal`` and ``-shm`` beside it).
ARKITEKT_FOLDER_IGNORED = [
    "*.json",
    "*.temp",
    "cache/",
    "servers/",
    "rekuest_journal.db*",
    "rekuest_state.db*",
]


def ensure_ignored(path: str) -> None:
    """Write the ignore file at ``path``, or add the patterns an older one lacks."""
    if not os.path.exists(path):
        with open(path, "w") as f:
            f.write("# Hiding Arkitekt credentials, caches and journals\n")
            f.write("\n".join(ARKITEKT_FOLDER_IGNORED) + "\n")
        return

    with open(path) as f:
        content = f.read()
    present = {line.strip() for line in content.splitlines()}
    missing = [pattern for pattern in ARKITEKT_FOLDER_IGNORED if pattern not in present]
    if missing:
        with open(path, "a") as f:
            if content and not content.endswith("\n"):
                f.write("\n")
            f.write("\n".join(missing) + "\n")


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
                "jhnnsrs.arkitekt",
            ]
        }
    }

    with open(devcontainer_file, "w") as f:
        json.dump(devcontainer_content, f, indent=4)
