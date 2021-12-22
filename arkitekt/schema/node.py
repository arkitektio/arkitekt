from abc import abstractmethod
from contextvars import Context
from arkitekt.messages.postman.reserve.reserve_transition import ReserveState
from arkitekt.monitor.monitor import Monitor
from arkitekt.schema.enums import NodeType
from arkitekt.schema.ports import AllArgPort, AllKwargPort, AllReturnPort
from arkitekt.graphql.node import NODE_CREATE_QUERY, NODE_GET_QUERY
from enum import Enum
from typing import Any, List, Optional, Union
from arkitekt.contracts.reservation import Reservation
from herre.access.model import GraphQLModel
from rich.table import Table

from koil.loop import koil, koil_gen




class Node(GraphQLModel):
    """Abstract distributed Function or Generator

    Node is arkitekts abstraction of a distributed function.
    They are drawn by applications and constitute a typed
    function specification. Nodes themselver are not 
    implementations (i.e they have are just documentation)
    
    An implementation of a Node provided by an App is a 
    Template. A running instance of this is provided for by
    an active Provision.

    Assigning arguments through a Node always involve an
    intermediary step of a reservation, where you are creating
    a unique link to specified provisions. Through this
    arkitekt achieves paralleization.

    Nodes belong to repositories. A repository is just a
    collection of nodes.

    Apps that enable original functions, with their own
    documentation will put these nodes in their repository.

    Apps can also pass a node as a template paramter, indicating
    that this Node will be an implemntation and not create a
    new node.

    Attributes:
        type (NodeType):
        args: A list of ArgPorts that specify types and desired widgets
        kwargs: A list of ArgPorts that specify types and desired widgets
        returns: A list of ArgPorts that specify types and desired widgets
    """
    name: Optional[str]
    description: Optional[str]
    package: Optional[str]
    interface: Optional[str]
    args: Optional[List[AllArgPort]]
    kwargs: Optional[List[AllKwargPort]]
    returns: Optional[List[AllReturnPort]]
    type: Optional[NodeType]


    def reserve(self, reference: str = None,
        provision: str = None, 
        monitor: Monitor = None,
        ignore_node_exceptions=False,
        transition_hook=None,
        with_log=False,
        enter_on=[ReserveState.ACTIVE], 
        exit_on=[ReserveState.ERROR, ReserveState.CANCELLED, ReserveState.CRITICAL],
        context: Context =None,
        loop=None,
         **params)-> Reservation:
        """Reserve

        reserve takes a Node and returns a reservation instance, this
        a Reservation is a Context Manager that establishes a long
        lasting link for the duration of the assignments with provisions
        
        If called without the persist attributes, reservations are ephemeral
        and will be put as inactive once you exit the context manager or the
        transport to arkitekt disconnects.

        If you want to reuse a reservation you can ask for arkitekt to persist
        the reservation so it will not be deactivated on leaving the context
        manager. Make sure to save the reservation reference for this task.
        This should be used sparely as their is no guarentee that arkitekt (
        or an admin) will not clean between to runs.

        Args:
            reference (str, optional): [description]. Defaults to None.
            provision (str, optional): [description]. Defaults to None.
            monitor (Monitor, optional): [description]. Defaults to None.
            ignore_node_exceptions (bool, optional): [description]. Defaults to False.
            transition_hook ([type], optional): [description]. Defaults to None.
            with_log (bool, optional): [description]. Defaults to False.
            enter_on (list, optional): [States when of the reservation where we will enter the context manager. Defaults to [ReserveState.ACTIVE].
            exit_on (list, optional): [description]. Defaults to [ReserveState.ERROR, ReserveState.CANCELLED, ReserveState.CRITICAL].
            context (Context, optional): [description]. Defaults to None.
            loop ([type], optional): [description]. Defaults to None.

        Returns:
            Reservation: [description]
        """
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
        if self.type == NodeType.FUNCTION:
            return koil(self.call_async_func(*args, **kwargs))

        if self.type == NodeType.GENERATOR:
            return koil_gen(self.call_async_gen(*args, **kwargs))


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





