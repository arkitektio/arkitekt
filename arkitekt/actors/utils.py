from arkitekt.api.schema import LogLevelInput
from arkitekt.actors.vars import get_current_assignation_helper


async def alog(message: str, level: LogLevelInput = LogLevelInput.DEBUG) -> None:
    await get_current_assignation_helper().alog(message, level)
