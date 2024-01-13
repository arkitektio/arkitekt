"""
This module contains the types for the apps
depending on the builder used.

This module imports all the apps and their types
and sets them as attributes on the App class, if they are available.
If they are not available, they are set to Any, so that we can add 
an import exception to the app.


"""
from koil.composition import Composition
from typing import TYPE_CHECKING
from arkitekt.model import Manifest
from arkitekt.apps.fallbacks import ImportException

import logging


logger = logging.getLogger(__name__)

try:
    from arkitekt.apps.service.rekuest import ArkitektRekuest
except ImportError:
    ArkitektRekuest = ImportException  # type: ignore


try:
    from arkitekt.apps.service.kluster import ArkitektKluster
except ImportError:
    ArkitektKluster = ImportException  # type: ignore


try:
    from arkitekt.apps.service.rekuest_next import ArkitektRekuestNext
except ImportError:
    ArkitektRekuestNext = ImportException  # type: ignore

try:
    from arkitekt.apps.service.fakts_qt import ArkitektFaktsQt
except ImportError:
    ArkitektFaktsQt = ImportException

try:
    from arkitekt.apps.service.herre_qt import ArkitektHerreQt
except ImportError:
    ArkitektHerreQt = ImportException


try:
    from arkitekt.apps.service.mikro import ArkitektMikro
except ImportError:
    ArkitektMikro = ImportException  # type: ignore
try:
    from arkitekt.apps.service.mikro_next import ArkitektMikroNext
except ImportError:
    ArkitektMikroNext = ImportException  # type: ignore
try:
    from arkitekt.apps.service.herre import ArkitektHerre
except ImportError:
    ArkitektHerre = ImportException  # type: ignore
try:
    from arkitekt.apps.service.fluss import ArkitektFluss
except ImportError:
    ArkitektFluss = ImportException  # type: ignore
try:
    from arkitekt.apps.service.unlok import ArkitektUnlok
except ImportError:
    ArkitektUnlok = ImportException  # type: ignore
try:
    from arkitekt.apps.service.omero_ark import ArkitektOmeroArk
except ImportError:
    ArkitektOmeroArk = ImportException  # type: ignore


try:
    from arkitekt.apps.service.fakts import ArkitektFakts
except ImportError:
    ArkitektFakts = ImportException  # type: ignore


try:
    from arkitekt.apps.service.fakts_next import ArkitektFaktsNext, Manifest
except ImportError:
    ArkitektFaktsNext = ImportException  # type: ignore


if TYPE_CHECKING:
    from arkitekt.apps.service.fakts import ArkitektFakts
    from arkitekt.apps.service.fakts_next import ArkitektFaktsNext
    from arkitekt.apps.service.rekuest import ArkitektRekuest
    from arkitekt.apps.service.omero_ark import ArkitektOmeroArk
    from arkitekt.apps.service.herre import ArkitektHerre
    from arkitekt.apps.service.mikro import ArkitektMikro
    from arkitekt.apps.service.mikro_next import ArkitektMikroNext
    from arkitekt.apps.service.fluss import ArkitektFluss
    from arkitekt.apps.service.unlok import ArkitektUnlok
    from arkitekt.apps.service.rekuest_next import ArkitektRekuestNext
    from arkitekt.apps.service.herre_qt import ArkitektHerreQt
    from arkitekt.apps.service.kluster import ArkitektKluster
    from arkitekt.apps.service.fakts_qt import ArkitektFaktsQt


class App(Composition):
    """An app that is built with the easy builder"""

    manifest: Manifest
    fakts: ArkitektFakts
    herre: ArkitektHerre
    rekuest: ArkitektRekuest
    mikro: ArkitektMikro
    fluss: ArkitektFluss
    unlok: ArkitektUnlok
    omero_ark: ArkitektOmeroArk
    kluster: ArkitektKluster


class EasyApp(Composition):
    """An app that is built with the easy builder"""

    manifest: Manifest
    fakts: ArkitektFakts
    herre: ArkitektHerre
    rekuest: ArkitektRekuest
    mikro: ArkitektMikro
    fluss: ArkitektFluss
    unlok: ArkitektUnlok
    omero_ark: ArkitektOmeroArk
    kluster: ArkitektKluster


class NextApp(Composition):
    """An app that is built with the next builder"""

    manifest: Manifest
    fakts: ArkitektFaktsNext
    herre: ArkitektHerre
    rekuest: ArkitektRekuestNext
    mikro: ArkitektMikroNext
    fluss: ArkitektFluss
    unlok: ArkitektUnlok
    omero_ark: ArkitektOmeroArk
    kluster: ArkitektKluster


class QtApp(Composition):
    manifest: Manifest
    fakts: ArkitektFaktsQt
    herre: ArkitektHerreQt
    rekuest: ArkitektRekuest
    mikro: ArkitektMikro
    unlok: ArkitektUnlok
    fluss: ArkitektFluss
    kluster: ArkitektKluster
