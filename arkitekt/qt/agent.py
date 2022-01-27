from typing import Dict
from arkitekt.actors.actify import actify
from arkitekt.agents.app import AppAgent
from arkitekt.api.schema import NodeFragment
from arkitekt.mixins.node import NodeMixin
from arkitekt.qt.actor import QtActor
from qtpy.QtCore import QObject, Signal
from arkitekt.messages.postman.assign.assign_cancelled import AssignCancelledMessage
from arkitekt.messages.postman.unassign.bounced_forwarded_unassign import (
    BouncedForwardedUnassignMessage,
)
from arkitekt.messages.postman.provide.provide_transition import (
    ProvideState,
    ProvideTransitionMessage,
)
from arkitekt.messages.postman.assign.assign_log import AssignLogMessage
from arkitekt.messages.postman.assign.assign_critical import AssignCriticalMessage
from arkitekt.messages.postman.assign.bounced_forwarded_assign import (
    BouncedForwardedAssignMessage,
)
from arkitekt.messages.postman.log import LogLevel
from arkitekt.messages.postman.provide.provide_log import ProvideLogMessage
import asyncio
from arkitekt.actors.base import Actor
from arkitekt.messages.postman.unprovide.bounced_unprovide import (
    BouncedUnprovideMessage,
)
from arkitekt.messages.postman.provide.bounced_provide import BouncedProvideMessage
from arkitekt.agents.base import Agent, AgentException
import logging
import uuid
from arkitekt.definition.define import prepare_definition
from arkitekt.structures.registry import (
    StructureRegistry,
    get_current_structure_registry,
)

logger = logging.getLogger(__name__)


class AgentSignals(QObject):
    provide = Signal(BouncedProvideMessage)
    unprovide = Signal(BouncedUnprovideMessage)
    provide_transition = Signal(ProvideTransitionMessage)

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)


class QtAgent(AppAgent, QObject):
    provide_signal = Signal()
    unprovide_signal = Signal()
    provision_signal = Signal(BouncedProvideMessage)
    unprovision_signal = Signal(BouncedUnprovideMessage)

    ACTOR_PENDING_MESSAGE = "Actor is Pending"

    def __init__(self, *args, strict=False, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.strict = strict
        self.assignFutures = {}
        self.provideFutures = {}
        self.unprovideFutures = {}
        self.appWorkers = {}

    async def on_bounced_provide(self, message: BouncedProvideMessage):
        self.provision_signal.emit(message)
        return await super().on_bounced_provide(message)

    async def on_bounced_unprovide(self, message: BouncedUnprovideMessage):
        self.unprovision_signal.emit(message)
        return await super().on_bounced_provide(message)

    def register_ui(
        self,
        function_query_or_node,
        widgets={},
        on_provide=None,
        on_unprovide=None,
        on_assign=None,
        timeout=500,
        structure_registry: StructureRegistry = None,
        **params
    ) -> QtActor:

        structure_registry = structure_registry or get_current_structure_registry()

        # Simple bypass for now
        defined_actor = QtActor(
            qt_assign=on_assign,
            qt_on_provide=on_provide,
            qt_on_unprovide=on_unprovide,
            timeout=timeout,
            structure_registry=structure_registry,
            **params
        )

        actor_builder = lambda: defined_actor

        if isinstance(function_query_or_node, str):
            self.registry.templatedUnqueriedNodes.append(
                ({"q": function_query_or_node}, actor_builder, params)
            )

        if isinstance(function_query_or_node, NodeFragment):
            self.registry.templatedNodes.append(
                (function_query_or_node, actor_builder, params)
            )

        else:
            defined_node = prepare_definition(
                function=function_query_or_node,
                widgets=widgets,
                structure_registry=structure_registry,
            )
            self.registry.templatedNewNodes.append(
                (defined_node, actor_builder, params)
            )

        return defined_actor

    def register_side(
        self,
        *args,
        widgets={},
        on_provide=None,
        on_unprovide=None,
        on_assign=None,
        timeout=500,
        structure_registry: StructureRegistry = None,
        **params
    ):

        # Simple bypass for now

        structure_registry = structure_registry or get_current_structure_registry()

        if len(args) == 0:
            raise NotImplementedError(
                "Please provide either a function to create a node or a function and a node or query as arguments"
            )

        defined_actor = actify(
            args[0],
            on_provide=on_provide,
            on_unprovide=on_unprovide,
            structure_registry=structure_registry,
            **params
        )

        if len(args) == 1:
            new_node = prepare_definition(
                function=args[0],
                widgets=widgets,
                structure_registry=structure_registry,
                **params
            )
            self.registry.templatedNewNodes.append((new_node, defined_actor, params))

        if len(args) == 2:
            query_or_node = args[1]

            if isinstance(query_or_node, str):
                self.registry.templatedUnqueriedNodes.append(
                    ({"q": query_or_node}, defined_actor, params)
                )

            if isinstance(query_or_node, NodeMixin):
                self.registry.templatedNodes.append(
                    (query_or_node, defined_actor, params)
                )

        return defined_actor

    async def approve_nodes_and_templates(self):
        await super().approve_nodes_and_templates()
        self.provide_signal.emit()
        return

    async def aprovide(self):
        try:
            await super().aprovide()
        except asyncio.CancelledError as e:
            self.unprovide_signal.emit()
            raise e
