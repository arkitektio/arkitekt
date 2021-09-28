from arkitekt.messages.postman.assign.assign_log import AssignLogMessage
from arkitekt.legacy.utils import get_running_loop
from arkitekt.threadvars import get_current_assign, get_current_transport, get_current_janus
from arkitekt.messages.postman.log import LogLevel


async def log_async(message, level: LogLevel = LogLevel.INFO):
    transport = get_current_transport()
    assign = get_current_assign()

    message = AssignLogMessage(
        data = {
            "message": str(message),
            "level": level
        },
        meta = {**assign.meta.dict(exclude={"type"})}
    )

    await transport.forward(message)



def log(message: str, level: LogLevel = LogLevel.INFO):
    """ Logs a message

    Depending on both the configuration of Arkitekt and the overwrite set on the
    Assignment, this logging will be sent (and persisted) on the Arkitekt server

    Args:
        message (sr): The Message you want to send
        level (DebugLevel, optional): The level of the log. Defaults to DebugLevel.INFO.

    Returns:
        [Future]: Returns a future if currently running in an event loop
    """
    try:
        event_loop = get_running_loop() # Check if we are in an event loop
    except RuntimeError:
        sync_q = get_current_janus()
        sync_q.put(("log", (message, level)))
        sync_q.join()
    else:
        return log_async(message, level=level)