""" Models for Arkitekt. Thiese include extensiosn for the Fakts Manifest and the User model."""

from pydantic import BaseModel, Field
from typing import List, Optional



class Requirement(BaseModel):
    service: str
    """ The service is the service that will be used to fill the key, it will be used to find the correct instance. It needs to fullfill
    the reverse domain naming scheme"""
    optional: bool = False 
    """ The optional flag indicates if the requirement is optional or not. Users should be able to use the client even if the requirement is not met. """
    description: Optional[str] = None
    """ The description is a human readable description of the requirement. Will be show to the user when asking for the requirement."""


def build_default_requirements() -> dict[str, Requirement]:
    return {
        "lok": Requirement(
            service="live.arkitekt.lok",
            description="An instance of Arkitekt Lok to authenticate the user",
        ),
        "rekuest": Requirement(
            service="live.arkitekt.rekuest",
            description="An instance of Arkitekt Rekuest to assign to nodes",
        ),
        "mikro": Requirement(
            service="live.arkitekt.mikro",
            description="An instance of Arkitekt Mikro to make requests to the user's data",
             optional=True,
        ),
        "fluss": Requirement(
            service="live.arkitekt.fluss",
            description="An instance of Arkitekt Fluss to make requests to the user's data",
            optional=False,
        ),
        "port": Requirement(
            service="live.arkitekt.port",
            description="An instance of Arkitekt Fluss to make requests to the user's data",
            optional=True,
        ),
        "datalayer": Requirement(
            service="live.arkitekt.datalayer",
            description="An instance of Arkitekt Datalayer to make requests to the user's data",
            optional=False,
        ),
    }




class Manifest(BaseModel):
    """A manifest for an app that can be installed in Arkitekt

    Manifests are used to describe apps that can be installed in Arkitekt.
    They provide information about the app, such as the
    its globally unique identifier, the version, the scopes it needs, etc.

    This Manifest is send to the Fakts server on initial app configuration,
    and is used to register the app with the Fakts server, which in turn
    will prompt the user to grant the app access to establish itself as
    an Arkitekt app (and therefore as an OAuth2 client) (see more in the
    Fakts documentation).

    """

    version: str
    """ The version of the app TODO: Should this be a semver? """
    identifier: str
    """ The globally unique identifier of the app: TODO: Should we check for a reverse domain name? """
    scopes: List[str]
    """ Scopes that this app should request from the user """
    logo: Optional[str]
    """ A URL to the logo of the app TODO: We should enforce this to be a http URL as local paths won't work """
    requirements: Optional[dict[str, Requirement]] = Field(default_factory=build_default_requirements)
    """ Requirements that this app has TODO: What are the requirements? """

    class Config:
        extra = "forbid"


class User(BaseModel):
    """A user of Arkitekt

    This model represents a user on Arkitekt. As herre is acgnostic to the
    user model, we need to provide a model that can be used to represent
    the Arkitekt user. This model is used by the
    :class:`herre.fakts.fakts_endpoint_fetcher.FaktsUserFetcher` to
    fetch the user from the associated Arkitekt Lok instance. This model
    is closely mimicking the OIDC user model, and is therefore compatible
    to represent OIDC users.

    """

    id: str = Field(alias="sub")
    """ The user's id (in lok, this is the user's sub(ject) ID)"""

    username: str = Field(alias="preferred_username")
    """ The user's preferred username """
    email: str = Field(alias="email")
    """ The user's preferred username """
