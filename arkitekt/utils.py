import os


def create_arkitekt_folder(with_cache: bool = True) -> str:
    """Creates the .arkitekt folder in the current directory.

    If the folder already exists, it does nothing.
    It automatically creates a .gitignore file, and a .dockerignore file,
    so that the Arkitekt credential files are not added to git.

    Parameters
    ----------
    with_cache : bool, optional
        Should we create a cache dir?, by default True

    Returns
    -------
    str
        The path to the .arkitekt folder.
    """
    os.makedirs(".arkitekt", exist_ok=True)
    if with_cache:
        os.makedirs(".arkitekt/cache", exist_ok=True)

    gitignore = os.path.join(".arkitekt", ".gitignore")
    dockerignore = os.path.join(".arkitekt", ".dockerignore")
    if not os.path.exists(gitignore):
        with open(gitignore, "w") as f:
            f.write(
                "# Hiding Arkitekt Credential files from git\n*.json\n*.temp\ncache/\nservers/"
            )
    if not os.path.exists(dockerignore):
        with open(dockerignore, "w") as f:
            f.write(
                "# Hiding Arkitekt Credential files from git\n*.json\n*.temp\ncache/\nservers/"
            )

    return os.path.abspath(".arkitekt")
