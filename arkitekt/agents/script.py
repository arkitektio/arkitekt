from typing import Dict
from arkitekt.actors.actify import actify
from arkitekt.definition.define import prepare_definition
from arkitekt.mixins.node import NodeMixin
from arkitekt.structures.registry import StructureRegistry

from .app import AppAgent


class ScriptAgent(AppAgent):
    def register(
        self,
        *args,
        widgets={},
        on_provide=None,
        on_unprovide=None,
        structure_registry: StructureRegistry = None,
        **params
    ):
        def real_decorator(function):
            # Simple bypass for now
            def wrapped_function(*args, **kwargs):
                return function(*args, **kwargs)

            actorBuilder = actify(
                function,
                on_provide=on_provide,
                on_unprovide=on_unprovide,
                structure_registry=structure_registry or self.structure_registry,
                **params
            )

            if len(args) == 0:
                defined_node = prepare_definition(
                    function=function,
                    widgets=widgets,
                    structure_registry=structure_registry or self.structure_registry,
                )
                self.actor_registry.templatedNewNodes.append(
                    (defined_node, actorBuilder, params)
                )

            if len(args) == 1:
                if isinstance(args[0], str):
                    self.actor_registry.templatedUnqueriedNodes.append(
                        ({"q": args[0]}, actorBuilder, params)
                    )

                if isinstance(args[0], NodeMixin):
                    self.actor_registry.templatedNodes.append(
                        (args[0], actorBuilder, params)
                    )

                # We are registering this as a template

            return wrapped_function

        return real_decorator
