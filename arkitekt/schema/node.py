from abc import abstractmethod
from contextvars import Context
from arkitekt.messages.postman.reserve.reserve_transition import ReserveState
from arkitekt.monitor.monitor import Monitor
from arkitekt.ui.sync_funcs import fill_args_kwargs_graphically
from arkitekt.schema.enums import NodeType
from arkitekt.schema.ports import DictArgPort, DictKwargPort, DictReturnPort, IntArgPort, IntKwargPort, IntReturnPort, ListArgPort, ListKwargPort, ListReturnPort, StringArgPort, StringKwargPort, StringReturnPort, StructureArgPort, StructureKwargPort, StructureReturnPort
from arkitekt.graphql.node import NODE_CREATE_QUERY, NODE_GET_QUERY
from enum import Enum
from typing import Any, List, Optional, Union
from arkitekt.contracts.reservation import Reservation
from herre.access.model import GraphQLModel
from herre.loop import loopify, loopify_gen
from rich.table import Table




class Node(GraphQLModel):
    name: Optional[str]
    description: Optional[str]
    package: Optional[str]
    interface: Optional[str]
    args: Optional[List[Union[StructureArgPort, StringArgPort, IntArgPort, ListArgPort, DictArgPort]]]
    kwargs: Optional[List[Union[StructureKwargPort, StringKwargPort, IntKwargPort, ListKwargPort, DictKwargPort]]]
    returns: Optional[List[Union[StructureReturnPort, StringReturnPort, IntReturnPort, ListReturnPort, DictReturnPort]]]
    type: Optional[NodeType]


    def reserve(self, reference: str = None,
        provision: str = None, 
        monitor: Monitor = None,
        ignore_node_exceptions=False,
        transition_hook=None,
        with_log=False,
        enter_on=[ReserveState.ACTIVE], 
        exit_on=[ReserveState.ERROR, ReserveState.CANCELLED],
        context: Context =None,
        loop=None,
         **params) -> Reservation:
        return Reservation(self, 
        reference=reference,
        provision=provision,
        monitor=monitor,
        transition_hook=transition_hook,
        with_log=with_log,
        enter_on=enter_on,
        ignore_node_exceptions=ignore_node_exceptions,
        exit_on=exit_on,
        context=context,
        loop = loop ,             
         **params)


    async def call_async_func(self,*args,  reserve_params={}, **kwargs):
        async with self.reserve(**reserve_params) as res:
            return await res.assign_async(*args, **kwargs)


    async def call_async_gen(self,*args,  reserve_params={}, **kwargs):
        async with self.reserve(**reserve_params) as res:
            async for result in res.stream_async(*args, **kwargs):
                yield result


    def __call__(self, *args: Any, fill_graphical= True, **kwargs) -> Any:
        """Call

        Call is a convenience on max function, its reserves the Node and wraps it either as
        an geneator (both async and non async depending on context) or call it as a function
        this should only be done if you know what you are doing. 
        
        Args:
            reserve_params (dict, optional): [description]. Defaults to {}.

        Returns:
            Any: Generator or Function
        """
        if fill_graphical: args, kwargs = fill_args_kwargs_graphically(self, args, kwargs)

        if self.type == NodeType.FUNCTION:
            return loopify(self.call_async_func(*args, **kwargs))

        if self.type == NodeType.GENERATOR:
            return loopify_gen(self.call_async_gen(*args, **kwargs))


    class Meta:
        register = False
        ward = "arkitekt"
        get = NODE_GET_QUERY
        create = NODE_CREATE_QUERY

    def __rich_repr__(self):
        yield self.name
        yield "args", self.args
        yield "kwargs", self.kwargs
        yield "returns", self.returns

    def __rich__(self):
        my_table = Table(title=f"Node: {self.name}", show_header=False)

        my_table.add_row("ID", str(self.id))
        my_table.add_row("Package", self.package)
        my_table.add_row("Interface", self.interface)
        my_table.add_row("Type", self.type)

        return my_table


    def _repr_html_(self):
        return f"""
        <div class="container" style="border:1px solid #00000f;padding: 4px;">
            <div class="item item-1 font-xl">{self.name}</div>
            <div class="item item-2">{self.package}/{self.interface}</div>
            <div class="item item-3">Args: {" ".join([port._repr_html_list() for port in self.args])}</div>
            <div class="item item-3">Kwargs: {" ".join([port.key for port in self.kwargs])}</div>
            <div class="item item-3">Returns: {" ".join([port.key for port in self.returns])}</div>
        </div>"""





