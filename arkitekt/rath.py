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

current_arkitekt_rath = contextvars.ContextVar("current_arkitekt_rath", default=None)


class ArkitektRath(rath.Rath):
    """_summary_

    Args:
        rath (_type_): _description_
    """

    async def __aenter__(self):
        await super().__aenter__()
        self._token = current_arkitekt_rath.set(self)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await super().__aexit__(exc_type, exc_val, exc_tb)
        current_arkitekt_rath.set(None)
