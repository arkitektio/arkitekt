import asyncio


# This is an example of an generator actor
async def gen(provision: int):

    # do something with provision

    while True:
        await asyncio.sleep(0.1)
        assignation = (
            yield  # on yield, the actor is paused and will receive new assignations
        )
        print("Hallo")
        assignation = yield  # on yield, the actor is paused and will receive new but using its previous state
        print("New Assignation:", assignation)
        raise Exception("Error")
