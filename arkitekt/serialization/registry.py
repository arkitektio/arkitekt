class StructureRegistryError(Exception):
    pass


class StructureRegistry:
    def __init__(self, register=True) -> None:

        self.identifier_expander_map = {}
        self.identifier_shrinker_map = {}
        self.structure_identifier_map = {}
        self.identifier_structure_map = {}

        self.structure_default_widget_map = {}

        if register:
            set_current_structure_registry(registry=self)

    def get_expanded_for_identifier(self, key):
        try:
            return self.identifier_expander_map[key]
        except KeyError as e:
            raise StructureRegistryError(f"{key} is not registered") from e

    def register_expander(self, key, expander):
        self.identifier_expander_map[key] = expander

    def get_widget_input(self, cls):
        return self.structure_default_widget_map.get(cls, None)

    def get_identifier_for_structure(self, cls):
        return self.structure_identifier_map[cls]

    def register_as_structure(
        self, cls, identifier=None, expand=None, shrink=None, default_widget=None
    ):
        if expand is None:
            assert hasattr(
                cls, "expand"
            ), "You need to specify an expand method or your class needs to implement an expand method"
            expand = cls.expand

        if shrink is None:
            assert hasattr(
                cls, "shrink"
            ), "You need to specify an shrink method or your class needs to implement a shrink method"
            shrink = cls.shrink

        if identifier is None:
            assert hasattr(
                cls, "identifier"
            ), "You need to specify a key or your class needs to implement a identifier attribute"
            identifier = cls.identifier

        if default_widget:
            pass

        self.identifier_expander_map[identifier] = expand
        self.identifier_shrinker_map[identifier] = shrink

        self.identifier_structure_map[identifier] = cls
        self.structure_identifier_map[cls] = identifier
        self.structure_default_widget_map[cls] = default_widget


STRUCTURE_REGISTRY = None


def get_current_structure_registry():
    global STRUCTURE_REGISTRY
    if not STRUCTURE_REGISTRY:
        STRUCTURE_REGISTRY = StructureRegistry()
    return STRUCTURE_REGISTRY


def set_current_structure_registry(registry):
    global STRUCTURE_REGISTRY
    STRUCTURE_REGISTRY = registry
