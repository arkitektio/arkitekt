from arkitekt.transport.base import Transport
from arkitekt.messages.postman.assign.bounced_assign import BouncedAssignMessage
import contextvars
import janus

assign_message = contextvars.ContextVar("assign_message")
transport = contextvars.ContextVar("transport")
janus_queue = contextvars.ContextVar("janus_queue")


def get_current_assign() -> BouncedAssignMessage:
    return assign_message.get()

def get_current_transport() -> Transport:
    return transport.get()

def get_current_janus() -> janus.Queue:
    return janus_queue.get()


