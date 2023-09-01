"""This constructs the type of a buildable app in the
current context
"""


from koil.composition import Composition
from typing import Any

NotAvailable = Any


try:
    from arkitekt.apps.rekuest import ArkitektRekuest
except ImportError as e:
    ArkitektRekuest = NotAvailable
try:
    from arkitekt.apps.reaktion_rekuest import ArkitektRekuest
except ImportError as e:
    ArkitektRekuest = ArkitektRekuest  # Overwriting the non scheduling one
try:
    from arkitekt.apps.mikro import ArkitektMikro
except ImportError as e:
    ArkitektMikro = NotAvailable
try:
    from arkitekt.apps.mikro_next import ArkitektMikroNext
except ImportError as e:
    ArkitektMikroNext = NotAvailable
try:
    from arkitekt.apps.herre import ArkitektHerre
except ImportError as e:
    ArkitektHerre = NotAvailable
try:
    from arkitekt.apps.fluss import ArkitektFluss
except ImportError as e:
    ArkitektFluss = NotAvailable
try:
    from arkitekt.apps.unlok import ArkitektUnlok
except ImportError as e:
    ArkitektUnlok = NotAvailable
try:
    from arkitekt.apps.fakts import ArkitektFakts, Manifest
except ImportError as e:
    Manifest = Any
    ArkitektFakts = NotAvailable


class App(Composition):
    manifest: Any
    fakts: ArkitektFakts
    herre: ArkitektHerre
    rekuest: ArkitektRekuest
    mikro: ArkitektMikro
    mikro_next: ArkitektMikroNext
    fluss: ArkitektFluss
    unlok: ArkitektUnlok
