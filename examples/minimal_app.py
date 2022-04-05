import asyncio
from enum import Enum

from arkitekt.app import ArkitektApp


app = ArkitektApp()


@app.arkitekt.register()
async def basic_yield(
    interval: int = 2,
    nana: bool = True,
) -> int:
    """Basic Yield

    Streams an increasing integer every interval

    Args:
        interval (int, optional): The Interval. Defaults to 2.
        yield_type (YieldType, optional): The Type of Yielding. Defaults to Yields Every Second

    Returns:
        int: The Yielded Integer (increasing)

    Yields:
        Iterator[int]: The Yielded Integer
    """

    i = 0
    while True:
        await asyncio.sleep(interval)
        yield i
        i += 1
        if i == 7:
            break


with app:
    app.arkitekt.run()
