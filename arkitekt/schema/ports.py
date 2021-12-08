from abc import abstractmethod
from enum import Enum
import inspect
from arkitekt.packers.models.base import StructureModel
from arkitekt.schema.widgets import AllWidgets, QueryWidget, SearchWidget, SliderWidget
from arkitekt.packers.structure import BoundType, Structure
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, validator
from herre.access.object import GraphQLObject
from arkitekt.packers.registry import get_packer_registry
from typing import ForwardRef
import asyncio


class Port(GraphQLObject):
    key: Optional[str]
    description: Optional[str]
    label: Optional[str]

    @classmethod
    def from_params(cls, **kwargs):
        # TODO: This weird widget conversion thing needs to stop, type GraphQLOBject correctly
        port = cls(
            __typename=cls.__name__, **kwargs
        )  # We ensure creation of a proper object)
        return port


class ArgPort(Port):
    widget: Optional[AllWidgets]

    def _repr_html_list(self):
        nana = f"""
        <div class="container" style="border:1px solid #00000f;padding: 4px;">
            <div class="item item-1 font-xl">{self.key}</div>
            <div class="item item-2">{self.description}</div>
        """
        if self.widget:
            nana += self.widget._repr_html_list()
        return nana + "</div>"


class IntExpandShrink:
    async def expand(self, value, **kwargs):
        return int(value) if value is not None else getattr(self, "defaultInt", None)

    async def shrink(self, instance, **kwargs):
        return int(instance) if instance is not None else None

    def to_type(self):
        return int


class BoolExpandShrink:
    async def expand(self, value, **kwargs):
        return bool(value) if value is not None else getattr(self, "defaultBool", None)

    async def shrink(self, instance, **kwargs):
        return bool(instance) if instance is not None else None

    def to_type(self):
        return bool


class EnumExpandShrink:
    async def expand(self, value, **kwargs):
        return (
            next(
                (
                    key
                    for key, optionvalue in self.options.items()
                    if optionvalue == value
                ),
                None,
            )
            if value is not None
            else getattr(self, "defaultOption", None)
        )

    async def shrink(self, instance, **kwargs):
        return self.options[instance] if instance else None

    def to_type(self):
        return Enum


class StringExpandShrink:
    async def expand(self, value, **kwargs):
        return str(value) if value is not None else getattr(self, "defaultString", None)

    async def shrink(self, instance, **kwargs):
        return str(instance) if instance is not None else None

    def to_type(self):
        return str


class StructureExpandShrink:
    @classmethod
    def from_structure(cls, structure: Structure, **overwrites):
        meta = structure.get_structure_meta()
        return cls.from_params(**{**meta.dict(), **overwrites})

    async def expand(self, value, transpile=True):
        if value is None:
            value = getattr(self, "defaultID", None)

        if value is None:
            return None

        structure = get_packer_registry().get_structure(self.identifier)
        return await structure.expand(value)

    async def shrink(self, instance, **kwargs):
        if instance is None:
            return None

        if hasattr(instance, "shrink"):
            return await instance.shrink()
        # Instance we are trying to shrink needs to be transpile to the required model
        from arkitekt.packers.transpilers.registry import get_transpiler_registry

        transpiler = get_transpiler_registry().get_transpiler(
            instance.__class__.__name__, self.identifier
        )
        transpiled_instance = await transpiler.transpile(instance)
        return await transpiled_instance.shrink()

    def to_type(self):
        return get_packer_registry().get_structure(self.identifier)


class ListExpandShrink:
    async def expand(self, value, **kwargs):
        value = getattr(self, "defaultList", None)

        return (
            await asyncio.gather(*[self.child.expand(item, **kwargs) for item in value])
            if value is not None
            else None
        )

    async def shrink(self, instance, **kwargs):
        assert isinstance(
            instance, list
        ), f"ListPorts only accept lists! Got {instance}"

        return (
            await asyncio.gather(
                *[self.child.shrink(item, **kwargs) for item in instance]
            )
            if instance is not None
            else None
        )

    def to_type(self):
        return List[self.child.to_type()]


class DictExpandShrink:
    async def expand(self, value, **kwargs):
        value = getattr(self, "defaultList", None)

        return (
            {
                key: await self.child.expand(item, **kwargs)
                for key, item in value.items()
            }
            if value is not None
            else None
        )

    async def shrink(self, instance, **kwargs):
        return (
            {
                key: await self.child.shrink(item, **kwargs)
                for key, item in instance.items()
            }
            if instance is not None
            else None
        )

    def to_type(self):
        return Dict[self.child.to_type()]


# Args
class EnumArgPort(ArgPort, EnumExpandShrink):
    options: Optional[dict]
    pass


class IntArgPort(ArgPort, IntExpandShrink):
    pass


class BoolArgPort(ArgPort, BoolExpandShrink):
    pass


class StringArgPort(ArgPort, StringExpandShrink):
    pass


class StructureArgPort(ArgPort, StructureExpandShrink):
    identifier: str
    bound: BoundType = BoundType.GLOBAL


ListArgPort = ForwardRef("ListArgPort")


class ListArgPort(ListExpandShrink, ArgPort):
    child: Union[IntArgPort, StructureArgPort, StringArgPort, ListArgPort]


ListArgPort.update_forward_refs()

DictArgPort = ForwardRef("DictArgPort")


class DictArgPort(DictExpandShrink, ArgPort):
    child: Union[IntArgPort, StructureArgPort, StringArgPort, ListArgPort]


DictArgPort.update_forward_refs()
# Kwargs


class KwargPort(Port):
    widget: Optional[AllWidgets]


class IntKwargPort(KwargPort, IntExpandShrink):
    defaultInt: Optional[int]

    @classmethod
    def from_params(cls, widget=None, default=None, **kwargs):
        # TODO: This weird widget conversion thing needs to stop, type GraphQLOBject correctly
        port = cls(
            __typename=cls.__name__,
            widget=widget.dict() if widget else None,
            defaultInt=default,
            **kwargs,
        )  # We ensure creation of a proper object)
        return port


class BoolKwargPort(KwargPort, BoolExpandShrink):
    defaultBool: Optional[bool]

    @classmethod
    def from_params(cls, widget=None, default=None, **kwargs):
        # TODO: This weird widget conversion thing needs to stop, type GraphQLOBject correctly
        port = cls(
            __typename=cls.__name__,
            widget=widget.dict() if widget else None,
            defaultBool=default,
            **kwargs,
        )  # We ensure creation of a proper object)
        return port


class EnumKwargPort(KwargPort, EnumExpandShrink):
    defaultOption: Any
    options: Optional[dict]
    pass

    @classmethod
    def from_params(cls, widget=None, default=None, **kwargs):
        port = cls(
            __typename=cls.__name__,
            widget=widget.dict() if widget else None,
            defaultOption=default._value_,
            **kwargs,
        )  # We ensure creation of a proper object)
        return port


class StringKwargPort(KwargPort, StringExpandShrink):
    defaultString: Optional[str]

    @classmethod
    def from_params(cls, widget=None, default=None, **kwargs):
        # TODO: This weird widget conversion thing needs to stop, type GraphQLOBject correctly
        port = cls(
            __typename=cls.__name__,
            widget=widget.dict() if widget else None,
            defaultString=default,
            **kwargs,
        )  # We ensure creation of a proper object)
        return port


class StructureKwargPort(KwargPort, StructureExpandShrink):
    defaultID: Optional[str]
    identifier: str

    @classmethod
    def from_params(cls, widget=None, default=None, **kwargs):
        # TODO: This weird widget conversion thing needs to stop, type GraphQLOBject correctly
        port = cls(
            __typename=cls.__name__,
            widget=widget.dict() if widget else None,
            defaultID=default,
            **kwargs,
        )  # We ensure creation of a proper object)
        return port


ListKwargPort = ForwardRef("ListKwargPort")


class ListKwargPort(KwargPort, ListExpandShrink):
    defaultList: Optional[List]
    child: Union[IntKwargPort, StructureKwargPort, StringKwargPort, ListKwargPort]

    @classmethod
    def from_params(cls, widget=None, default=None, **kwargs):
        # TODO: This weird widget conversion thing needs to stop, type GraphQLOBject correctly
        port = cls(
            __typename=cls.__name__,
            widget=widget.dict() if widget else None,
            defaultList=default,
            **kwargs,
        )  # We ensure creation of a proper object)
        return port


ListKwargPort.update_forward_refs()

DictKwargPort = ForwardRef("DictKwargPort")


class DictKwargPort(KwargPort, DictExpandShrink):
    defaultDict: Optional[Dict]
    child: Union[
        IntKwargPort, StructureKwargPort, StringKwargPort, ListKwargPort, DictKwargPort
    ]

    @classmethod
    def from_params(cls, widget=None, default=None, **kwargs):
        # TODO: This weird widget conversion thing needs to stop, type GraphQLOBject correctly
        port = cls(
            __typename=cls.__name__,
            widget=widget.dict() if widget else None,
            defaultDict=default,
            **kwargs,
        )  # We ensure creation of a proper object)
        return port


DictKwargPort.update_forward_refs()


# Returns


class ReturnPort(Port):
    pass


class StructureReturnPort(ReturnPort, StructureExpandShrink):
    identifier: str


class IntReturnPort(ReturnPort, IntExpandShrink):
    pass


class BoolReturnPort(ReturnPort, BoolExpandShrink):
    pass


class StringReturnPort(ReturnPort, StringExpandShrink):
    pass


ListReturnPort = ForwardRef("ListReturnPort")


class ListReturnPort(ReturnPort, ListExpandShrink):
    child: Union[IntReturnPort, StructureReturnPort, StringReturnPort, ListReturnPort]


ListReturnPort.update_forward_refs()


DictReturnPort = ForwardRef("DictReturnPort")


class DictReturnPort(ReturnPort, DictExpandShrink):
    child: Union[
        IntReturnPort,
        StructureReturnPort,
        StringReturnPort,
        ListReturnPort,
        DictReturnPort,
    ]


DictReturnPort.update_forward_refs()


AllArgPort = Union[
    StructureArgPort,
    StringArgPort,
    IntArgPort,
    ListArgPort,
    DictArgPort,
    EnumArgPort,
    BoolArgPort,
]
AllKwargPort = Union[
    StructureKwargPort,
    StringKwargPort,
    IntKwargPort,
    ListKwargPort,
    DictKwargPort,
    EnumKwargPort,
    BoolKwargPort,
]
AllReturnPort = Union[
    StructureReturnPort,
    StringReturnPort,
    IntReturnPort,
    ListReturnPort,
    DictReturnPort,
    BoolReturnPort,
]
