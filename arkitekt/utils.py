import os


def create_arkitekt_folder(with_cache: bool = True):
    """Create the arkitekt folder"""
    os.makedirs(".arkitekt", exist_ok=True)
    if with_cache:
        os.makedirs(".arkitekt/cache", exist_ok=True)

    gitignore = os.path.join(".arkitekt", ".gitignore")
    dockerignore = os.path.join(".arkitekt", ".dockerignore")
    if not os.path.exists(gitignore):
        with open(gitignore, "w") as f:
            f.write(
                "# Hiding Arkitekt Credential files from git\n*.json\n*.temp\ncache/"
            )
    if not os.path.exists(dockerignore):
        with open(dockerignore, "w") as f:
            f.write(
                "# Hiding Arkitekt Credential files from git\n*.json\n*.temp\ncache/"
            )

    return ".arkitekt"
