import asyncio
from typing import Dict, List, Tuple
from .structures import SecondObject, SecondSerializableObject, SerializableObject


def karl(rep: str, name: str = None) -> str:
    """Karl

    Karl takes a a representation and does magic stuff

    Args:
        rep (str): Nougat
        name (str, optional): Bugat

    Returns:
        Representation: The Returned Representation
    """
    return "tested"


def karl_structure(
    rep: SerializableObject, name: SerializableObject = None
) -> SecondSerializableObject:
    """Karl

    Karl takes a a representation and does magic stuff

    Args:
        rep (SerializableObject): Nougat
        name (SerializableObject, optional): Bugat

    Returns:
        SecondSerializableObject: The Returned Representation
    """
    return "tested"


def complex_karl(
    rep: List[str], nana: Dict[str, int], name: str = None
) -> Tuple[List[str], int]:
    """Complex Karl

    Nananan

    Args:
        rep (List[str]): arg
        rep (List[str]): arg2
        name (str, optional): kwarg. Defaults to None.

    Returns:
        Tuple[List[str], int]: return, return2
    """
    return ["tested"], 6


def structured_gen(
    rep: List[SerializableObject], name: Dict[str, SerializableObject] = None
) -> Tuple[str, Dict[str, SecondSerializableObject]]:
    """Structured Karl

    Naoinaoainao

    Args:
        rep (List[SerializableObject]): [description]
        name (Dict[str, SerializableObject], optional): [description]. Defaults to None.

    Returns:
        str: [description]
        Dict[str, SecondSerializableObject]: [description]
    """
    yield "tested"


def function_with_side_register(
    rep: List[SecondObject], name: Dict[str, SecondObject] = None
) -> Tuple[str, Dict[str, SecondObject]]:
    """Structured Karl

    Naoinaoainao

    Args:
        rep (List[SecondObject]): [description]
        name (Dict[str, SerializableObject], optional): [description]. Defaults to None.

    Returns:
        str: [description]
        Dict[str, SecondSerializableObject]: [description]
    """
    yield "tested", {"peter": SecondObject(6)}


async def function_with_side_register_async(
    rep: List[SecondObject], name: Dict[str, SecondObject] = None
) -> Tuple[str, Dict[str, SecondObject]]:
    """function_with_side_register_async

    Naoinaoainao

    Args:
        rep (List[SecondObject]): [description]
        name (Dict[str, SerializableObject], optional): [description]. Defaults to None.

    Returns:
        str: [description]
        Dict[str, SecondSerializableObject]: [description]
    """
    while True:
        await asyncio.sleep(0.2)
        yield "tested", {"peter": SecondObject(6)}
