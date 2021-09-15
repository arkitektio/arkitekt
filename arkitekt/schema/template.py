from arkitekt.graphql.template import UPDATE_OR_CREATE_TEMPLATE, TEMPLATE_GET_QUERY
from typing import Any, List, Optional, Union

from herre.access.model import GraphQLModel
from arkitekt.schema.node import Node
from herre.loop import loopify, loopify_gen
from herre.wards.graphql import ParsedQuery


class Provider(GraphQLModel):
    name: Optional[str]

    class Meta:
        register = False
        ward = "arkitekt"



class Template(GraphQLModel):
    node: Optional[Node]
    provider: Optional[Provider]
    channel: Optional[str]


    class Meta:
        register = False
        ward = "arkitekt"
        create = UPDATE_OR_CREATE_TEMPLATE
        get = TEMPLATE_GET_QUERY






