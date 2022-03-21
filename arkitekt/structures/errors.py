class ExpandingError(Exception):
    pass


class ShrinkingError(Exception):
    pass


class StructureRegistryError(Exception):
    pass


class StructureOverwriteError(StructureRegistryError):
    pass


class StructureDefinitionError(StructureRegistryError):
    pass
