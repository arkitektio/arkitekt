from arkitekt.structures.registry import StructureRegistry
from arkitekt.definition.registry import DefinitionRegistry
import fakts


class App:
    def __init__(
        self,
        fakts: fakts.Fakts,
        structure_registry: StructureRegistry = None,
        definition_registry: DefinitionRegistry = None,
    ) -> None:

        self.arkitekt = FaktsArkitekt()

        self.structure_registry = structure_registry or StructureRegistry()
        self.definition_registry = definition_registry or DefinitionRegistry()
