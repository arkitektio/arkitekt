from arkitekt.graphql.template import UPDATE_OR_CREATE_TEMPLATE, TEMPLATE_GET_QUERY
from typing import Any, List, Optional, Union
from arkitekt.schema.basic import Registry

from herre.access.model import GraphQLModel
from arkitekt.schema.node import Node
from herre.wards.graphql import ParsedQuery


class Template(GraphQLModel):
    node: Optional[Node]
    registry: Optional[Registry]
    channel: Optional[str]
    version: Optional[str]

    class Meta:
        register = False
        ward = "arkitekt"
        create = UPDATE_OR_CREATE_TEMPLATE
        get = TEMPLATE_GET_QUERY
