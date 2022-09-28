from arkitekt.apps.connected import ConnectedApp
from fakts import Fakts
from fakts.grants.remote.device_code import DeviceCodeGrant
from rekuest.widgets import SliderWidget
import asyncio 
import logging

logger = logging.getLogger(__name__)

app = ConnectedApp(
    fakts=Fakts(subapp="tetst", grant=DeviceCodeGrant(open_browser=True, name="basic"))
)



@app.rekuest.register(
    widgets={"interval": SliderWidget(min=0, max=15)}, maximumInstancesPerAgent=2
)
async def basic_yield(
    interval: int = 2,
    should_break: int = -1,
) -> int:
    """Basic Yield

    Streams an increasing integer every interval

    Args:
        interval (int, optional): The Interval. Defaults to 2.
        should_break (int, optional): Whether to break. Defaults to -1 (never breaking).

    Returns:
        int: The Yielded Integer (increasing)

    Yields:
        Iterator[int]: The Yielded Integer
    """
    try:
        i = 0
        while True:
            await asyncio.sleep(interval)
            yield i
            i += 1
            if i == should_break:
                break
    except asyncio.CancelledError as e:
        logger.info("Cancelled")
        await asyncio.sleep(3)
        raise e


with app:
    app.rekuest.run()