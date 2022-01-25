from typing import Dict
from arkitekt.actors.actify import actify
from arkitekt.definition.define import prepare_definition
from arkitekt.mixins.node import NodeMixin

from .app import AppAgent


class ScriptAgent(AppAgent):
    def register(self, *args, widgets={}, on_provide=None, on_unprovide=None, **params):
        def real_decorator(function):
            # Simple bypass for now
            def wrapped_function(*args, **kwargs):
                return function(*args, **kwargs)

            actorBuilder = actify(
                function, on_provide=on_provide, on_unprovide=on_unprovide, **params
            )

            if len(args) == 0:
                defined_node = prepare_definition(function=function, widgets=widgets)
                self.templatedNewNodes.append((defined_node, actorBuilder, params))

            if len(args) == 1:
                if isinstance(args[0], str):
                    self.templatedUnqueriedNodes.append(
                        ({"q": args[0]}, actorBuilder, params)
                    )

                if isinstance(args[0], NodeMixin):
                    self.templatedNodes.append((args[0], actorBuilder, params))

                # We are registering this as a template

            return wrapped_function

        return real_decorator
