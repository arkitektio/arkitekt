"""Errors raised by arkitekt itself.

The ones here are about an app's *phase*. An app is configured first and built
when it is entered, so asking a configured app for something that only exists
once it is built is a mistake worth naming.
"""


class ArkitektError(Exception):
    """Base class for the errors arkitekt raises."""


class AppNotBuiltError(ArkitektError, RuntimeError):
    """Something that only exists once an app is built was asked for before that.

    Inherits ``RuntimeError`` as well, because that is what this used to raise and
    what callers catch.
    """


class AppAlreadyBuiltError(ArkitektError, RuntimeError):
    """An app's configuration was changed after it had already been built.

    What an app is made of is settled when it is built -- the manifest is what it
    tells the server it is, and what its fakts cache is keyed on -- so changing it
    afterwards would silently not take effect.
    """


__all__ = ["ArkitektError", "AppNotBuiltError", "AppAlreadyBuiltError"]
