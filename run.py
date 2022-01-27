from rich.logging import RichHandler
from arkitekt.actors.registry import ActorRegistry
from arkitekt.actors.utils import log
from arkitekt.agents.script import ScriptAgent
from arkitekt.messages.postman.log import LogLevel
from arkitekt.schema.widgets import SliderWidget
from arkitekt.structures.registry import StructureRegistry
from fakts.grants.endpoint import EndpointGrant, FaktsEndpoint
import asyncio
from enum import Enum
from fakts import Fakts
import logging
from arkitekt import register


logging.basicConfig(level="INFO", handlers=[RichHandler()])

fakts = Fakts(subapp="basic", grants=[EndpointGrant(FaktsEndpoint())])


actor_registry = ActorRegistry()
structure_registry = StructureRegistry()


agent = ScriptAgent(with_monitor=False)


class YieldType(Enum):
    YIELD_EVERY = "Yields every second"
    YIELD_NONE = "Yields never"


@register(
    widgets={"interval": SliderWidget(min=0, max=15)},
    maximumInstancesPerAgent=2,
    actor_registry=actor_registry,
    structure_registry=structure_registry,
)
async def basic_yield(
    interval: int = 2,
    nana: bool = True,
) -> int:
    """Basic Yield

    Streams an increasing integer every interval

    Args:
        interval (int, optional): The Interval. Defaults to 2.
        yield_type (YieldType, optional): The Type of Yielding. Defaults to Yields Every Second
        really (bool, optional): Should we really break?

    Returns:
        int: The Yielded Integer (increasing)

    Yields:
        Iterator[int]: The Yielded Integer
    """

    print(interval)
    print(nana)

    i = 0
    print("Called")
    while True:
        await asyncio.sleep(interval)

        print("Called")
        yield i
        await log("Nanana this", LogLevel.INFO)
        i += 1
        if i == 7:
            break


@register()
async def add_three(number: int) -> int:
    """Add three

    Adds three to the incoming number

    Args:
        number (int): The number we want to add three to

    Returns:
        int: number + int
    """
    try:
        print("Is being called")
        return number + 3
    except asyncio.CancelledError as e:
        print("Ohhh babye pleeeeese")
        raise e


@register()
async def add_to_numbers(a: int, b: int) -> int:
    """Adds two Numbers

    Adds three to the incoming number

    Args:
        a (int): number a
        b (int): number b

    Returns:
        int: a + b
    """
    return a + b


agent.provide()
