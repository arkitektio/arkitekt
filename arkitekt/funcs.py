from arkitekt.rath import ArkitektRath, current_arkitekt_rath


def execute(operation, variables, rath: ArkitektRath = None):
    rath = rath or current_arkitekt_rath.get()
    return operation(**rath.execute(operation.Meta.document, variables).data)


async def aexecute(operation, variables, rath: ArkitektRath = None):
    rath = rath or current_arkitekt_rath.get()
    x = await rath.aexecute(operation.Meta.document, variables)
    return operation(**x.data)


def subscribe(operation, variables, rath: ArkitektRath = None):
    rath = rath or current_arkitekt_rath.get()

    for event in rath.subscribe(operation.Meta.document, variables):
        yield operation(**event.data)


async def asubscribe(operation, variables, rath: ArkitektRath = None):
    rath = rath or current_arkitekt_rath.get()
    async for event in rath.asubscribe(operation.Meta.document, variables):
        yield operation(**event.data)
