from arkitekt.config import ArkitektConfig
from herre.wards.graphql import GraphQLWardConfig, ParsedQuery, GraphQLWard
from herre.herre import get_current_herre
from herre.wards.query import TypedQuery
from arkitekt.api.schema import TranscriptFragment, anegotiate


class ArkitektWard(GraphQLWard):
    configClass = ArkitektConfig

    class Meta:
        key = "arkitekt"

    async def negotiate(self) -> TranscriptFragment:
        return await anegotiate()


class gql(TypedQuery):
    ward_key = "arkitekt"
