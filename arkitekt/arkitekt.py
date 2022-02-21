"""The initialization Function for stuff

This module demonstrates documentation as specified by the `Google
Python Style Guide`_. Docstrings may extend over multiple lines.
Sections are created with a section header and a colon followed by a
block of indented text.

Example:
    Examples can be given using either the ``Example`` or ``Examples``
    sections. Sections support any reStructuredText formatting, including
    literal blocks:

        ```python
        print("Hello world")




        ```



        $ python example_google.py

Section breaks are created by resuming unindented text. Section breaks
are also implicitly created anytime a new section starts.

Attributes:
    module_level_variable1 (int): Module level variables may be documented in
        either the ``Attributes`` section of the module docstring, or in an
        inline docstring immediately following the variable.

        Either form is acceptable, but the two should not be mixed. Choose
        one convention to document module level variables and be consistent
        with it.

Todo:
    * For module TODOs
    * You have to also use ``sphinx.ext.todo`` extension

.. _Google Python Style Guide:   
http://google.github.io/styleguide/pyguide.html

"""


import os
from arkitekt.errors import NoArkitektFound
from rath import rath
import contextvars
import logging

current_arkitekt = contextvars.ContextVar("current_arkitekt", default=None)
GLOBAL_ARKITEKT = None


logger = logging.getLogger(__name__)


def set_current_arkitekt(herre, set_global=True):
    """_summary_

    Args:
        herre (_type_): _description_
        set_global (bool, optional): _description_. Defaults to True.
    """
    global GLOBAL_ARKITEKT
    current_arkitekt.set(herre)
    if set_global:
        GLOBAL_ARKITEKT = herre


def set_global_arkitekt(herre):
    global GLOBAL_ARKITEKT
    GLOBAL_ARKITEKT = herre


def get_current_arkitekt(allow_global=True):
    global GLOBAL_ARKITEKT
    arkitekt = current_arkitekt.get()

    if not arkitekt:
        if not allow_global:
            raise NoArkitektFound(
                "No current mikro found and global mikro are not allowed"
            )
        if not GLOBAL_ARKITEKT:
            if os.getenv("ARKITEKT_ALLOW_ARKITEKT_GLOBAL", "True") == "True":
                try:

                    from arkitekt.fakts.arkitekt import FaktsArkitekt

                    GLOBAL_ARKITEKT = FaktsArkitekt()
                    return GLOBAL_ARKITEKT
                except ImportError as e:
                    raise NoArkitektFound("Error creating Fakts Mikro") from e
            else:
                raise NoArkitektFound(
                    "No current mikro found and and no global mikro found"
                )

        return GLOBAL_ARKITEKT

    return arkitekt


class Arkitekt(rath.Rath):
    """_summary_

    Args:
        rath (_type_): _description_
    """

    pass
