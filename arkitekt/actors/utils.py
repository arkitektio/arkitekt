from arkitekt.api.schema import LogLevelInput
from arkitekt.actors.vars import current_actor_helper


async def alog(message: str, level: LogLevelInput = LogLevelInput.DEBUG) -> None:
    await current_actor_helper.get().alog(message, level)
