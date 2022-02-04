from pydantic import BaseModel
from arkitekt.arkitekt import get_current_arkitekt, Arkitekt
from rath.turms.operation import GraphQLOperation


class GraphQLMikroOperation(GraphQLOperation):
    @classmethod
    def execute(cls, variables, arkitekt: Arkitekt = None):
        arkitekt = arkitekt or get_current_arkitekt()
        return cls(**arkitekt.execute(cls.get_meta().document, variables).data)

    @classmethod
    async def aexecute(cls, variables, arkitekt: Arkitekt = None):
        arkitekt = arkitekt or get_current_arkitekt()
        return cls(**(await arkitekt.aexecute(cls.get_meta().document, variables)).data)

    class Meta:
        abstract = True


class GraphQLQuery(GraphQLMikroOperation):
    class Meta:
        abstract = True


class GraphQLMutation(GraphQLMikroOperation):
    class Meta:
        abstract = True


class GraphQLSubscription(GraphQLMikroOperation):
    class Meta:
        abstract = True
