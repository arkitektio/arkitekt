from bergen.console import console
from bergen.debugging import DebugLevel
from bergen.handlers import AssignHandler, ReserveHandler, ProvideHandler
import contextvars
from bergen.legacy.utils import get_running_loop


assign_handler_context  = contextvars.ContextVar('assign_handler', default=None)
provide_handler_context = contextvars.ContextVar("provide_handler", default=None)

bounce_context = contextvars.ContextVar("bounce_context", default=None)
queue_context = contextvars.ContextVar("queue_context", default=None)



async def log_async(message, level: DebugLevel = DebugLevel.INFO):
    handler: AssignHandler = assign_handler_context.get()
    await handler.log(message, level)


def useUser():
    context = bounce_context.get()
    assert context is not None, "You cannot get the App if you are not running inside a (functional Actor)"
    return context.user


def useApp():
    context = bounce_context.get()
    assert context is not None, "You cannot get the App if you are not running inside a (functional Actor)"
    return context.app



def log(message: str, level: DebugLevel = DebugLevel.INFO):
    """ Logs a message

    Depending on both the configuration of Arkitekt and the overwrite set on the
    Assignment, this logging will be sent (and persisted) on the Arkitekt server

    Args:
        message (sr): The Message you want to send
        level (DebugLevel, optional): The level of the log. Defaults to DebugLevel.INFO.

    Returns:
        [Future]: Returns a future if currently running in an event loop
    """
    message = str(message)

    try:
        event_loop = get_running_loop()
    except RuntimeError:
        sync_q = queue_context.get()
        sync_q.put(("log", (message, level)))
        sync_q.join()
    else:
        return log_async(message, level=level)