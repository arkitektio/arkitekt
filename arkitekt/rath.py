from rath import rath
import contextvars

current_arkitekt_rath = contextvars.ContextVar("current_arkitekt_rath", default=None)


class ArkitektRath(rath.Rath):
    """_summary_

    Args:
        rath (_type_): _description_
    """

    async def __aenter__(self):
        await super().__aenter__()
        current_arkitekt_rath.set(self)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await super().__aexit__(exc_type, exc_val, exc_tb)
        current_arkitekt_rath.set(None)
