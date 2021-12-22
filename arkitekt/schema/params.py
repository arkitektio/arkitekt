from typing import Optional
from pydantic.main import BaseModel
from arkitekt.messages import ReserveParams as ReserveParamsMessage
from herre.access.object import GraphQLObject


class ReserveParams(ReserveParamsMessage):
    def to_variable(self):
        return self.dict()


class TemplateParams(GraphQLObject):
    maximumInstances: Optional[int]
    maximumInstancesPerAgent: Optional[int]
