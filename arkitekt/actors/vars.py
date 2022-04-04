import contextvars
from typing import Any
import janus
from arkitekt.actors.helper import ActorHelper

from arkitekt.messages import Assignation

current_assignation = contextvars.ContextVar("current_assignation")
transport = contextvars.ContextVar("transport")
actor = contextvars.ContextVar("transport")
current_janus_queue = contextvars.ContextVar("current_janus_queue")
current_provision_context = contextvars.ContextVar("current_provision_context")


current_actor_helper = contextvars.ContextVar("current_actor_helper")


def get_current_assignation() -> Assignation:
    return current_assignation.get()


def get_provision_context() -> Any:
    return current_provision_context.get()


def get_current_janus() -> janus.Queue:
    return current_janus_queue.get()


def get_current_actor_helper() -> ActorHelper:
    pass