"""
This module contains the types for the apps
depending on the builder used.
This module imports all the apps and their types
and sets them as attributes on the App class, if they are available.
If they are not available, they are set to Any, so that we can add
an import exception to the app.


"""

import logging
from typing import Any, Dict, TYPE_CHECKING
from koil import unkoil
from koil.composition import Composition
from fakts_next import Fakts
from fakts_next.models import Manifest


if TYPE_CHECKING:
    from rekuest_next.rekuest import RekuestNext


logger = logging.getLogger(__name__)


class App(Composition):
    """An app that is built with the easy builder"""

    fakts: Fakts
    manifest: Manifest
    services: Dict[str, Any]

    @property
    def rekuest(self) -> "RekuestNext":
        """Get the rekuest service"""
        if "rekuest" not in self.services:
            raise ValueError("Rekuest service is not available")
        return self.services["rekuest"]

    def run(self):
        """Run the app by calling rekuest.run()"""
        return unkoil(self.rekuest.arun)

    def run_test(self):
        """Run the app tests by calling rekuest.run_tests()"""
        return unkoil(self.rekuest.arun_tests)

    async def arun(self):
        """Run the app asynchronously"""
        return await self.rekuest.arun()

    def run_detached(self):
        """Run the app detached"""
        return self.rekuest.run_detached()

    def register(self, *args, **kwargs):
        """Register a service"""

        return self.rekuest.register(*args, **kwargs)

    def register_startup(self, *args, **kwargs):
        """Register a startup service"""
        return self.rekuest.register_startup(*args, **kwargs)

    def register_background(self, *args, **kwargs):
        """Register a background service"""
        return self.rekuest.register_background(*args, **kwargs)

    def register_blok(self, *args, **kwargs):
        """Register a blok"""
        return self.rekuest.register_blok(*args, **kwargs)

    def state(self, *args, **kwargs):
        """Decorator to define a state class."""
        return self.rekuest.state(*args, **kwargs)

    def startup(self, *args, **kwargs):
        """Decorator to define a startup function."""
        return self.rekuest.register_startup(*args, **kwargs)

    def background(self, *args, **kwargs):
        """Decorator to define a background function."""
        return self.rekuest.register_background(*args, **kwargs)

    async def __aenter__(self):
        await super().__aenter__()
        for service in self.services.values():
            await service.__aenter__()

        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        for service in self.services.values():
            await service.__aexit__(exc_type, exc_value, traceback)
