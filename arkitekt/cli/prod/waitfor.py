import asyncio
from importlib import import_module
from typing import List
import logging

logger = logging.getLogger(__name__)


async def retriebable_login(herre, max_retries=5, retry_period=5, retry=0):
    if retry == max_retries:
        raise Exception(f"We exceeded the retries for {herre}. Fatal Error!")
    try:
        await herre.alogin()
        print(f"{herre} Connected")
        return "Ok"
    except Exception as e:
        print(e)
        print(f"Sleeping for {retry_period}")
        await asyncio.sleep(retry_period)
        await retriebable_login(
            herre, max_retries=max_retries, retry_period=retry_period, retry=retry + 1
        )


async def wait_for_connection(modules: List[str]):
    """Wits for connection

    Import required Modules for this instance to run and tries to
    connect to the wards.

    TODO: The wards are not checked if alive at the same time
    at the end

    Args:
        modules (List[str]): The imported modules
    """

    ward_registry = get_ward_registry()

    imports = [import_module(module) for module in modules]

    herre = get_current_herre()
    await retriebable_login(herre)

    await asyncio.gather(*[retriable_connect(ward=ward) for ward in wardInstances])

    print("We are done whoop whoop")
