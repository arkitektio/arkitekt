from arkitekt.transport.base import Transport
from arkitekt.messages.postman.assign.bounced_assign import BouncedAssignMessage
import contextvars
import janus
import threading

assign_message = contextvars.ContextVar("assign_message")
transport = contextvars.ContextVar("transport")
janus_queue = contextvars.ContextVar("janus_queue")
cancel_event = contextvars.ContextVar("cancel_event")


def get_current_assign() -> BouncedAssignMessage:
    return assign_message.get()

def get_current_transport() -> Transport:
    return transport.get()

def get_current_janus() -> janus.Queue:
    return janus_queue.get()

def get_current_cancel_event() -> threading.Event:
    return cancel_event.get()

