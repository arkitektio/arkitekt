from arkitekt.config import ArkitektConfig
from herre.wards.graphql import GraphQLWardConfig, ParsedQuery, GraphQLWard
from herre.herre import  get_current_herre




class ArkitektWard(GraphQLWard):
    configClass = ArkitektConfig

    class Meta:
        key = "arkitekt"


    async def negotiate(self):
        from arkitekt.schema.negotiation import Transcript
        transcript_query = await self.arun(ParsedQuery("""mutation Negotiate {
            negotiate {
                postman {
                    type
                    kwargs
                }
            } 
        }"""))
        return Transcript(**transcript_query["negotiate"])
