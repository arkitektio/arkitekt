from typing import Optional, Union
from herre.access.model import GraphQLModel
from herre.types import User, App


class Repository(GraphQLModel):
    name: Optional[str]

    class Meta:
        register = False
        ward = "arkitekt"


class AppRepository(Repository):
    app: Optional[App]

    class Meta:
        register = True
        ward = "arkitekt"


class MirrorRepository(Repository):
    url: Optional[str]

    class Meta:
        register = True
        ward = "arkitekt"


AllRepository = Union[MirrorRepository, AppRepository]


class Registry(GraphQLModel):
    app: Optional[App]
    user: Optional[User]

    class Meta:
        register = False
        ward = "arkitekt"
