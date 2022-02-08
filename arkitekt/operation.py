from pydantic import BaseModel
from arkitekt.arkitekt import get_current_arkitekt, Arkitekt
from rath.turms.operation import GraphQLOperation


class GraphQLArkitektOperation(GraphQLOperation):
    @classmethod
    def execute(cls, variables, arkitekt: Arkitekt = None):
        arkitekt = arkitekt or get_current_arkitekt()
        return cls(**arkitekt.execute(cls.get_meta().document, variables).data)

    @classmethod
    async def aexecute(cls, variables, arkitekt: Arkitekt = None):
        arkitekt = arkitekt or get_current_arkitekt()
        x = await arkitekt.aexecute(cls.get_meta().document, variables)
        return cls(**x.data)

    @classmethod
    def subscribe(cls, variables, mikro: Arkitekt = None):
        mikro = mikro or get_current_arkitekt()

        for event in mikro.subscribe(cls.get_meta().document, variables):
            yield cls(**event.data)

    @classmethod
    async def asubscribe(cls, variables, mikro: Arkitekt = None):
        mikro = mikro or get_current_arkitekt()
        async for event in mikro.asubscribe(cls.get_meta().document, variables):
            yield cls(**event.data)

    class Meta:
        abstract = True


class GraphQLQuery(GraphQLArkitektOperation):
    class Meta:
        abstract = True


class GraphQLMutation(GraphQLArkitektOperation):
    class Meta:
        abstract = True


class GraphQLSubscription(GraphQLArkitektOperation):
    class Meta:
        abstract = True
