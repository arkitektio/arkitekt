import asyncio
from typing import Any
from arkitekt.api.schema import KwargPortFragment, PortType


async def aexpand(port: KwargPortFragment, value: Any, structure_registry=None) -> Any:
    """Expand a value through a port

    Args:
        port (ArgPortFragment): Port to expand to
        value (Any): Value to expand
    Returns:
        Any: Expanded value

    """
    if port.type == PortType.DICT:
        return {
            key: await aexpand(port.child, value, structure_registry)
            for key, value in value.items()
        }

    if port.type == PortType.LIST:
        return await asyncio.gather(
            *[
                aexpand(port.child, item, structure_registry=structure_registry)
                for item in value
            ]
        )

    if port.type == PortType.INT:
        return int(value) if value else int(port.default)

    if port.type == PortType.STRUCTURE:
        return (
            await structure_registry.get_expander_for_identifier(port.identifier)(value)
            if value
            else None
        )

    if port.type == PortType.ENUM:
        if value == None:
            value = port.default

        return str(value) if value else None

    if port.type == PortType.BOOL:
        if value == None:
            value = port.default

        return bool(value) if value else None

    if port.type == PortType.STRING:
        if value == None:
            value = port.default

        return str(value) if value else None

    raise NotImplementedError("Should be implemented by subclass")


async def ashrink(port: KwargPortFragment, value: Any, structure_registry=None) -> Any:
    """Expand a value through a port

    Args:
        port (ArgPortFragment): Port to expand to
        value (Any): Value to expand
    Returns:
        Any: Expanded value

    """
    if port.type == PortType.DICT:
        return {
            key: await ashrink(port.child, value, structure_registry)
            for key, value in value.items()
        }

    if port.type == PortType.LIST:
        return await asyncio.gather(
            *[
                ashrink(port.child, item, structure_registry=structure_registry)
                for item in value
            ]
        )

    if port.type == PortType.INT:
        return int(value) if value else int(port.default)

    if port.type == PortType.STRUCTURE:
        return await structure_registry.get_shrinker_for_identifier(port.identifier)(
            value
        )

    if port.type == PortType.ENUM:
        return str(value)

    if port.type == PortType.BOOL:
        return bool(value)

    if port.type == PortType.STRING:
        return str(value)

    raise NotImplementedError(f"Should be implemented by subclass {port}")
