import docker


def dockerbuild(**kwargs):

    """Deploy to a docker container.

    Args:

        **kwargs: Keyword arguments passed to the docker client.

    Returns:

        A docker container object.

    """

    return {"type": "docker", "image": "arkitekt/deployers:latest"}