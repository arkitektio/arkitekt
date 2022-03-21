import contextvars
from typing import Any, Awaitable, Callable, Dict, Optional, Type

from arkitekt.api.schema import WidgetInput
from .errors import (
    StructureDefinitionError,
    StructureOverwriteError,
    StructureRegistryError,
)
from pydantic import BaseModel


current_structure_registry = contextvars.ContextVar(
    "current_structure_registry", default=None
)


async def id_shrink(self):
    return self.id


class StructureRegistry(BaseModel):
    copy_from_default: bool = False
    allow_overwrites: bool = True
    allow_auto_register: bool = False

    _identifier_expander_map: Dict[str, Callable[[str], Awaitable[Any]]] = {}
    _identifier_shrinker_map: Dict[str, Callable[[Any], Awaitable[str]]] = {}
    _structure_identifier_map: Dict[Type, str] = {}
    _structure_default_widget_map: Dict[Type, WidgetInput] = {}
    _identifier_structure_map: Dict[str, Type] = {}

    _token: contextvars.Token = None

    def get_expander_for_identifier(self, key):
        try:
            return self._identifier_expander_map[key]
        except KeyError as e:
            raise StructureRegistryError(f"{key} is not registered") from e

    def get_shrinker_for_identifier(self, key):
        try:
            return self._identifier_shrinker_map[key]
        except KeyError as e:
            raise StructureRegistryError(f"{key} is not registered") from e

    def register_expander(self, key, expander):
        self._identifier_expander_map[key] = expander

    def get_widget_input(self, cls) -> Optional[WidgetInput]:
        return self._structure_default_widget_map.get(cls, None)

    def get_identifier_for_structure(self, cls):
        try:
            return self._structure_identifier_map[cls]
        except KeyError as e:
            if self.allow_auto_register:
                try:
                    self.register_as_structure(cls)
                    return self._structure_identifier_map[cls]
                except StructureDefinitionError as e:
                    raise StructureDefinitionError(
                        f"{cls} was not registered and could not be registered automatically"
                    ) from e
            else:
                raise StructureRegistryError(
                    f"{cls} is not registered and allow_auto_register is set to False. Please make sure to register this type beforehand or set allow_auto_register to True"
                ) from e

    def register_as_structure(
        self,
        cls,
        identifier=None,
        expand=None,
        shrink=None,
        default_widget=None,
        id_shrink=True,
    ):
        if expand is None:
            if not hasattr(cls, "expand"):
                raise StructureDefinitionError(
                    f"You need to pass 'expand' method or {cls} needs to implement a expand method"
                )
            expand = cls.expand

        if shrink is None:
            if not hasattr(cls, "shrink"):
                if issubclass(cls, BaseModel):
                    if "id" in cls.__fields__:
                        cls.shrink = id_shrink
                    else:
                        raise StructureDefinitionError(
                            f"You need to pass 'shrink' method or {cls} needs to implement a shrink method. A BaseModel can be automatically shrinked by providing an id field"
                        )
                else:
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

        if identifier in self._identifier_structure_map and not self.allow_overwrites:
            raise StructureOverwriteError(
                f"{identifier} is already registered. Previously registered {self._identifier_structure_map[identifier]}"
            )

        self._identifier_expander_map[identifier] = expand
        self._identifier_shrinker_map[identifier] = shrink
        self._identifier_structure_map[identifier] = cls
        self._structure_identifier_map[cls] = identifier
        self._structure_default_widget_map[cls] = default_widget

    async def __aenter__(self):
        current_structure_registry.set(self)
        return self

    async def __exit__(self, exc_type, exc_val, exc_tb):
        current_structure_registry.set(None)

    class Config:
        arbitrary_types_allowed = True
        underscore_attrs_are_private = True


DEFAULT_STRUCTURE_REGISTRY = None


def get_default_structure_registry():
    global DEFAULT_STRUCTURE_REGISTRY
    if not DEFAULT_STRUCTURE_REGISTRY:
        DEFAULT_STRUCTURE_REGISTRY = StructureRegistry()
    return DEFAULT_STRUCTURE_REGISTRY


def get_current_structure_registry(allow_default=True):
    return current_structure_registry.get(get_default_structure_registry())


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
