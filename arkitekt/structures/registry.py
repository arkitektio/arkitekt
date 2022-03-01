from typing import Any, Awaitable, Callable, Dict, Type


class StructureRegistryError(Exception):
    pass


class StructureOverwriteError(StructureRegistryError):
    pass


class StructureDefinitionError(StructureRegistryError):
    pass


class StructureRegistry:
    def __init__(
        self, register=True, allow_overwrites=True, allow_auto_register=True
    ) -> None:

        self.identifier_expander_map: Dict[str, Callable[[str], Awaitable[Any]]] = {}
        self.identifier_shrinker_map: Dict[str, Callable[[Any], Awaitable[str]]] = {}
        self.structure_identifier_map: Dict[Type, str] = {}
        self.identifier_structure_map: Dict[str, Type] = {}
        self.allow_overwrites = allow_overwrites
        self.allow_auto_register = allow_auto_register

        self.structure_default_widget_map = {}

        if register:
            set_current_structure_registry(registry=self)

    def get_expander_for_identifier(self, key):
        try:
            return self.identifier_expander_map[key]
        except KeyError as e:
            raise StructureRegistryError(f"{key} is not registered") from e

    def get_shrinker_for_identifier(self, key):
        try:
            return self.identifier_shrinker_map[key]
        except KeyError as e:
            raise StructureRegistryError(f"{key} is not registered") from e

    def register_expander(self, key, expander):
        self.identifier_expander_map[key] = expander

    def get_widget_input(self, cls):
        return self.structure_default_widget_map.get(cls, None)

    def get_identifier_for_structure(self, cls):
        try:
            return self.structure_identifier_map[cls]
        except KeyError as e:
            if self.allow_auto_register:
                try:
                    self.register_as_structure(cls)
                    return self.structure_identifier_map[cls]
                except StructureDefinitionError as e:
                    raise StructureDefinitionError(
                        f"{cls} was not registered and could not be registered automatically"
                    ) from e
            else:
                raise StructureRegistryError(
                    f"{cls} is not registered and allow_auto_register is set to False. Please make sure to register this type beforehand or set allow_auto_register to True"
                ) from e

    def register_as_structure(
        self, cls, identifier=None, expand=None, shrink=None, default_widget=None
    ):
        if expand is None:
            if not hasattr(cls, "expand"):
                raise StructureDefinitionError(
                    f"You need to pass 'expand' method or {cls} needs to implement a expand method"
                )
            expand = cls.expand

        if shrink is None:
            if not hasattr(cls, "shrink"):
                raise StructureDefinitionError(
                    f"You need to pass 'shrink' method or {cls} needs to implement a shrink method"
                )
            shrink = cls.shrink

        if identifier is None:
            if not hasattr(cls, "get_identifier"):
                raise StructureDefinitionError(
                    f"You need to pass 'identifier' or  {cls} needs to implement a get_identifier method"
                )
            identifier = cls.get_identifier()

        if default_widget:
            pass

        if identifier in self.identifier_structure_map and not self.allow_overwrites:
            raise StructureOverwriteError(
                f"{identifier} is already registered. Previously registered {self.identifier_structure_map[identifier]}"
            )

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


def register_structure(
    identifier=None,
    expand=None,
    shrink=None,
    default_widget=None,
    registry: StructureRegistry = None,
):
    """A Decorator for registering a structure

    Args:
        identifier ([type], optional): [description]. Defaults to None.
        expand ([type], optional): [description]. Defaults to None.
        shrink ([type], optional): [description]. Defaults to None.
        default_widget ([type], optional): [description]. Defaults to None.
    """

    registry = registry or get_current_structure_registry()

    def func(cls):

        registry.register_as_structure(cls, identifier, expand, shrink, default_widget)
        return cls

    return func
