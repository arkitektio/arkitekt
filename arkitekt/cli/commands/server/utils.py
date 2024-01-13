import os 
from typing import List


def compile_options() -> List[str]:
    """ Compiles the available options for the server up and down commands:
     
      All deployments in the .arkitekt/deployments folder
    """
    deployments = os.path.join(os.getcwd(), ".arkitekt", "deployments")

    available_deployments = []

    if not os.path.exists(deployments):
        return available_deployments

    for deployment in os.listdir(deployments):
        if os.path.isdir(os.path.join(deployments, deployment)):
            available_deployments.append(deployment)

    return available_deployments
