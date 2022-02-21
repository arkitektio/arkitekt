import contextvars
import janus
import threading

from arkitekt.agents.messages import Assignation

current_assignation = contextvars.ContextVar("current_assignation")
transport = contextvars.ContextVar("transport")
current_janus_queue = contextvars.ContextVar("current_janus_queue")
current_cancel_event = contextvars.ContextVar("current_cancel_event")


def get_current_assignation() -> Assignation:
    return current_assignation.get()


def get_current_janus() -> janus.Queue:
    return current_janus_queue.get()


def get_current_cancel_event() -> threading.Event:
    return current_cancel_event.get()
