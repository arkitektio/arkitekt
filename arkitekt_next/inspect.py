import typing
from rekuest_next.structures.default import get_default_structure_registry
import subprocess
import sys
import webbrowser
import os
from rath.scalars import ID


def open_orkestrator_link(link: str):
    webbrowser.open(link)


class IDBearer(typing.Protocol):
    id: ID


def inspect(x: IDBearer) -> None:
    """
    Inspects the given object by opening it in the orkestrator.



    """
    structure_reg = get_default_structure_registry()

    identifier = structure_reg.get_identifier_for_cls(type(x))

    open_orkestrator_link(f"orkestrator://{identifier}/{x.id}")
