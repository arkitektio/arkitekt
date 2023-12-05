from typing import Any
from koil.composition import KoiledModel


class InstallModuleException(Exception):
    """An exception that is raised when a module is not installed."""

    pass


class ImportException(KoiledModel):
    """A pydantic model that raises an InstallModuleException when an attribute
    of a non-installed library is accessed.

    We use this to allow for optional imports of libraries that are not
    required for the core functionality of arkitekt, but that are required
    for some of the features. This allows us to install arkitekt without
    having to install all the dependencies. If a feature is used that requires
    a library that is not installed, we raise an InstallModuleException.

    Check the app builders for examples of how this is used.

    TODO: Maybe we should write better documentation for this.
    """

    import_exception: Exception
    install_library: str

    def __getattr__(self, __name: str) -> Any:
        """Override the __getattribute__ method to raise an InstallModuleException"""
        try:
            raise self.import_exception
        except Exception as e:
            raise InstallModuleException(
                f"This module is not installed! Please install the library {self.install_library} to use this feature. Cannot access attribute {__name}"
            ) from e

    class Config:
        arbitrary_types_allowed = True
