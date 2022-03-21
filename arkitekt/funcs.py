from arkitekt.rath import ArkitektRath, current_arkitekt_rath
from koil import unkoil
from koil.helpers import unkoil_gen


def execute(operation, variables, rath: ArkitektRath = None):
    return unkoil(aexecute, operation, variables, rath)


async def aexecute(operation, variables, rath: ArkitektRath = None):
    rath = rath or current_arkitekt_rath.get()
    x = await rath.aexecute(operation.Meta.document, variables)
    return operation(**x.data)


def subscribe(operation, variables, rath: ArkitektRath = None):
    return unkoil_gen(asubscribe, operation, variables, rath)


async def asubscribe(operation, variables, rath: ArkitektRath = None):
    rath = rath or current_arkitekt_rath.get()
    async for event in rath.asubscribe(operation.Meta.document, variables):
        yield operation(**event.data)
