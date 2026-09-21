"""Small helpers for the plugin commands."""


def search_username_in_docker_info(docker_info: str) -> str | None:
    """The Docker Hub username `docker info` reports, if it is logged in."""
    for line in docker_info.splitlines():
        if "Username" in line:
            return line.split(":")[1].strip()
    return None
