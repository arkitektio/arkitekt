import os
from typing import List


def compile_options() -> List[str]:
    """Compiles the available options for the server up and down commands:

    All deployments in the .arkitekt/deployments folder
    """
    deployments = os.path.join(os.getcwd(), ".dokker")

    available_deployments = []

    if not os.path.exists(deployments):
        return available_deployments

    for deployment in os.listdir(deployments):
        if os.path.isdir(os.path.join(deployments, deployment)):
            available_deployments.append(deployment)

    return available_deployments


def build_server_path(name: str) -> str:
    """Builds the path to the server

    Args:
        name (str): The name of the server

    Returns:
        str: The path to the server
    """
    return os.path.join(os.getcwd(), ".arkitekt", "servers", name)
