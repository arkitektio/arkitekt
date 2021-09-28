from abc import abstractmethod
from arkitekt.schema.widgets import AllWidgets, QueryWidget, SearchWidget, SliderWidget
from arkitekt.packers.structure import Structure
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
    transpile: Optional[str]

    @classmethod
    def from_params(cls, widget=None, **kwargs):
        #TODO: This weird widget conversion thing needs to stop, type GraphQLOBject correctly
        port = cls(__typename=cls.__name__, widget= widget.dict() if widget else None, **kwargs) # We ensure creation of a proper object)
        return port


    

class ArgPort(Port):
    widget: Optional[AllWidgets]

    def _repr_html_list(self):
        nana =  f"""
        <div class="container" style="border:1px solid #00000f;padding: 4px;">
            <div class="item item-1 font-xl">{self.key}</div>
            <div class="item item-2">{self.description}</div>
        """
        if self.widget: nana += self.widget._repr_html_list()
        return nana + "</div>"





class IntExpandShrink:

    async def expand(self, value,**kwargs):
        return int(value)

    async def shrink(self, instance,**kwargs):
       return int(instance)


    def to_type(self):
        return int


class StringExpandShrink:

    async def expand(self, value,**kwargs):
        return str(value)

    async def shrink(self, instance,**kwargs):
        return str(instance)

    def to_type(self):
        return str



class StructureExpandShrink:

    async def expand(self, value, transpile=True):
        if value is None: return None
        structure = get_packer_registry().get_structure(self.identifier)
        return await structure.expand(value)

    async def shrink(self, instance,**kwargs):
        if not instance: return None
        if isinstance(instance, Structure) or hasattr(instance, "shrink"): return await instance.shrink()
        # Instance we are trying to shrink needs to be transpile to the required model
        from arkitekt.packers.transpilers.registry import get_transpiler_registry
        transpiler = get_transpiler_registry().get_transpiler(instance.__class__.__name__, self.identifier)
        transpiled_instance = await transpiler.transpile(instance)
        return await transpiled_instance.shrink()

    def to_type(self):
        return get_packer_registry().get_structure(self.identifier)
    

class ListExpandShrink:

    async def expand(self, value,**kwargs):
        return await asyncio.gather(*[self.child.expand(item,**kwargs) for item in value])

    async def shrink(self, instance,**kwargs):
        assert isinstance(instance, list), f"ListPorts only accept lists! Got {instance}"
        return await asyncio.gather(*[self.child.shrink(item,**kwargs) for item in instance])

    def to_type(self):
        return List[self.child.to_type()]

class DictExpandShrink:

    async def expand(self, value,**kwargs):
        return {key: await self.child.expand(item,**kwargs) for key, item in value.items()}

    async def shrink(self, instance,**kwargs):
        return {key: await self.child.shrink(item,**kwargs) for key, item in instance.items()}

    def to_type(self):
        return Dict[self.child.to_type()]


# Args



class IntArgPort(ArgPort, IntExpandShrink):
    pass

class StringArgPort(ArgPort, StringExpandShrink):
    pass


class StructureArgPort(ArgPort,StructureExpandShrink):
    identifier: str


ListArgPort = ForwardRef('ListArgPort')
class ListArgPort(ListExpandShrink, ArgPort):
    child: Union[IntArgPort, StructureArgPort, StringArgPort, ListArgPort]


ListArgPort.update_forward_refs()

DictArgPort = ForwardRef('DictArgPort')
class DictArgPort(DictExpandShrink, ArgPort):
    child: Union[IntArgPort, StructureArgPort, StringArgPort, ListArgPort]


   


DictArgPort.update_forward_refs()
#Kwargs

class KwargPort(Port):
    widget: Optional[AllWidgets]


class IntKwargPort(KwargPort, IntExpandShrink):
    default: Optional[int]


class StringKwargPort(KwargPort, StringExpandShrink):
    default: Optional[str]

class StructureKwargPort(KwargPort, StructureExpandShrink):
    default: Optional[str]
    identifier: str

ListKwargPort = ForwardRef('ListKwargPort')
class ListKwargPort(KwargPort, ListExpandShrink):
    default: Optional[List]
    child: Union[IntKwargPort, StructureKwargPort, StringKwargPort, ListKwargPort]

ListKwargPort.update_forward_refs()

DictKwargPort = ForwardRef('DictKwargPort')
class DictKwargPort(KwargPort, DictExpandShrink):
    default: Optional[Dict]
    child: Union[IntKwargPort, StructureKwargPort, StringKwargPort, ListKwargPort, DictKwargPort]

DictKwargPort.update_forward_refs()



# Returns

class ReturnPort(Port):
    pass


class StructureReturnPort(ReturnPort, StructureExpandShrink):
    identifier: str

class IntReturnPort(ReturnPort, IntExpandShrink):
    pass

class StringReturnPort(ReturnPort, StringExpandShrink):
    pass

ListReturnPort = ForwardRef('ListReturnPort')
class ListReturnPort(ReturnPort, ListExpandShrink):
    child: Union[IntReturnPort, StructureReturnPort, StringReturnPort, ListReturnPort]

ListReturnPort.update_forward_refs()


DictReturnPort = ForwardRef('DictReturnPort')
class DictReturnPort(ReturnPort, DictExpandShrink):
    child: Union[IntReturnPort, StructureReturnPort, StringReturnPort, ListReturnPort, DictReturnPort]

DictReturnPort.update_forward_refs()

