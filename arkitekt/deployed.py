""" A deployed kluster instance package"""

from dokker import Deployment
import os
from koil.composition import Composition
from arkitekt.apps.types import EasyApp
from arkitekt.builders import easy
from dokker.projects.contrib.konstruktor import KonstruktorProject
from typing import Optional
from arkitekt.constants import REPO_URL


class ArkitektDeployment(Deployment):
    project: KonstruktorProject


def build_deployment(
    channel: str, name: Optional[str] = None, repo_url: str = REPO_URL
) -> ArkitektDeployment:
    """Builds a deploymen of kluster for testing

    This will return a deployment of kluster that is ready to be used for testing.
    It will have a health check that will check the graphql endpoint.

    Returns
    -------
    Deployment
        The deployment of kluster (dokker.Deployment)


    """
    project = KonstruktorProject(
        channel=channel,
        repo=repo_url,
        name=name,
    )

    deployment = ArkitektDeployment(project=project)
    deployment.add_health_check(
        url="http://localhost:8000/ht",
        service="lok",
        timeout=5,
        max_retries=10,
    )
    return deployment


async def token_loader() -> str:
    """Returns a token as defined in the static_token setting for kluster"""
    return "demo"


class DeployedArkitekt(Composition):
    """A deployed kluster instance

    THis is a composition of both a deployment of kluster-server
    (and kluster-gateway) and a client for that deployment. It is
    the fastest way to get a fully functioning kluster instance,
    ready for testing.


    """

    deployment: ArkitektDeployment
    app: EasyApp


def deployed(channel: str, *args, **kwargs) -> DeployedArkitekt:
    """Create a deployed kluster

    A deployed kluster is a composition of a deployment of the
    kluster server and a kluster client.
    This means a fully functioning kluster instance will be spun up when
    the context manager is entered.

    To inspect the deployment, use the `deployment` attribute.
    To interact with the kluster, use the `kluster` attribute.


    Returns
    -------
    DeployedKluster
        The deployed kluster instance (Composition)
    """

    url = "localhost:8000"
    # TODO: Retrieve the url from the deployment

    return DeployedArkitekt(
        deployment=build_deployment(channel),
        app=easy(*args, url=url, **kwargs),
    )
