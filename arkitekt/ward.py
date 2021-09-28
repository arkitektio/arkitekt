from arkitekt.schema.negotiation import Transcript
from herre.config.herre import BaseConfig
from herre.wards.graphql import ParsedQuery, GraphQLWard
from herre.auth import HerreClient


class ArkitektConfig(BaseConfig):
    host: str
    port: int
    secure: bool

    class Config:
        yaml_group = "arkitekt"
        env_prefix = "arkitekt_"


class ArkitektWard(GraphQLWard):

    class Meta:
        key = "arkitekt"

    def __init__(self, herre: HerreClient) -> None:
        self.config = ArkitektConfig.from_file(herre.config_path)
        self.transcript: Transcript = None
        super().__init__(herre, f"http://{self.config.host}:{self.config.port}/graphql")


    async def negotiate(self):
        transcript_query = await self.run(ParsedQuery("""mutation Negotiate {
            negotiate {
                postman {
                    type
                    kwargs
                }
            } 
        }"""))
        return Transcript(**transcript_query["negotiate"])
