import pydantic
from arkitekt.packers.registry import get_packer_registry
from arkitekt.packers.models.base import StructureModel
from herre.access.model import GraphQLModel
import logging

logger = logging.getLogger(__name__)






class GraphQLStructure(GraphQLModel, StructureModel):
    __typename: str

    @classmethod
    async def expand(cls, identifier):
        return await cls.asyncs.get(id=identifier)

    async def shrink(self):
        assert (
            self.id is not None
        ), "In order to send a Model through a Port you need to query 'id' in your GQL Query"
        return self.id

    @classmethod
    def register_model(cls, meta=None):
        super().register_model(meta=meta)
        logger.debug(f"Registering {cls} as Structure under identifier {meta}")
        get_packer_registry().register_structure(cls)
        

    class Meta:
        abstract = True
