from arkitekt.apps import Arkitekt
from fakts.grants.remote.device_code import DeviceCodeGrant
from fakts.fakts import Fakts
from fakts.grants import CacheGrant
from herre.grants import CacheGrant as HerreCacheGrant
from herre.grants.oauth2.refresh import RefreshGrant
from herre.grants.fakts import FaktsGrant
from fakts.discovery import StaticDiscovery
from herre import Herre
import logging
from koil.composition import PedanticKoil




def easy(
    identifier: str, version: str = "latest", url: str = "http://localhost:8000/f/", headless: bool = False, allow_sync_in_async: bool = True, log_level: str = "ERROR"
) -> Arkitekt:
    """Easy app creation

    A simple way to create an Arkitekt app with a device code grant
    it will cache the configuration in a file called `identifier`_token.json
    and the cache in a file called `identifier`_cache.json

    Args:
        identifier (str): The apps identifier
        version (str, optional): The apps verion. Defaults to "latest".
        url (_type_, optional): The app configuration url. Defaults to "http://localhost:8000/f/".
        headless (bool, optional): Do not open a browser window. Defaults to False.
        allow_sync_in_async (bool, optional): Should we allow the creation of a sync interface in an async loop (necessary for a sync interface in jupyter). Defaults to True.

    Returns:
        Arkitekt: _description_
    """

    try:
        from rich.logging import RichHandler

        logging.basicConfig(level=log_level, handlers=[RichHandler()])
    except ImportError:
        logging.basicConfig(level=log_level)


    return Arkitekt(
        title=identifier,
        koil=PedanticKoil(sync_in_async=allow_sync_in_async),
        fakts=Fakts(
            grant=CacheGrant(
                cache_file=f"{identifier}-{version}_cache.json",
                hash=f"{identifier}-{version}-{url}",
                grant=DeviceCodeGrant(
                    identifier=identifier,
                    version=version,
                    open_browser=not headless,
                    discovery=StaticDiscovery(base_url=url),
                ),
            )
        ),
        herre=Herre(
            grant=HerreCacheGrant(
                cache_file=f"{identifier}-{version}_herre_cache.json",
                hash=f"{identifier}-{version}-{url}",
                grant=RefreshGrant(grant=FaktsGrant()),
            ),
        ),
    )


def qt(version: str, identifier: str, parent) -> Arkitekt:
    """
    A simple way to create an Arkitekt app within a Qt application stilll
    utilizing a device code grant to authenticate the user on an application
    level
    """

    from koil.composition.qt import QtPedanticKoil

    return Arkitekt(
        koil=QtPedanticKoil(parent=parent),
        fakts=Fakts(
            grant=CacheGrant(
                cache_file=f"{identifier}-{version}_cache.json",
                grant=DeviceCodeGrant(
                    identifier=identifier,
                    version=version,

                ),
            )
        ),
        herre=Herre(
            grant=HerreCacheGrant(
                cache_file=f"{identifier}-{version}_herre_cache.json",
                hash=f"{identifier}-{version}",
                grant=FaktsGrant(),
            ),
        ),
    )


def publicqt(identifier: str, version: str = "latest",  parent = None) -> Arkitekt:
    """Public QtApp creation

    A simple way to create an Arkitekt app with a public grant (allowing users to sign
    in with the application ) utlizing a retrieve grant (necessating a previous configuration
    of the application on the server side)

    Args:
        identifier (str): The apps identifier
        version (str, optional): The apps verion. Defaults to "latest".
        parent (QtWidget, optional): The QtParent (for the login and server select widget). Defaults to None.

    Returns:
        Arkitekt: The Arkitekt app
    """

    from koil.composition.qt import QtPedanticKoil
    from herre.grants.fakts.fakts_login_screen import FaktsQtLoginScreen, LoginWidget
    from fakts.grants.remote.retrieve import RetrieveGrant
    from fakts.discovery.qt.selectable_beacon import SelectBeaconWidget, QtSelectableDiscovery


    x = SelectBeaconWidget(parent=parent)

    loginWindow = LoginWidget(identifier, version, parent=parent)

    app = Arkitekt(
        fakts=Fakts(
            grant=CacheGrant(
                skip_cache=True,
                cache_file=f"{identifier}-{version}_fakts_cache.json",
                grant=RetrieveGrant(
                            identifier=identifier,
                            version=version,
                            redirect_uri="http://localhost:6767",
                            discovery=QtSelectableDiscovery(
                                    widget=x,
                                ),
                        ),
            ),
            assert_groups={"mikro", "rekuest"},
        ),
        herre=Herre(
            grant=HerreCacheGrant(
                cache_file=f"{identifier}-{version}_herre_cache.json",
                hash=f"{identifier}-{version}",
                skip_cache=True,
                grant=FaktsQtLoginScreen(
                    widget=loginWindow,
                    auto_login=True,
                    grant=RefreshGrant(grant=FaktsGrant()),
                ),
            ),
        ),
    )

    return app


def flussi(
    identifier: str, version: str = "latest", url: str = "http://localhost:8000/f/"
):
    """
    A simple way to create an Arkitekt app with a device code grant
    it will cache the configuration in a file called `identifier`_token.json
    and the cache in a file called `identifier`_cache.json
    """

    from arkitekt.apps.fluss import ConnectedFluss

    return ConnectedFluss(
        fakts=Fakts(
            grant=CacheGrant(
                cache_file=f"{identifier}-{version}_cache.json",
                hash=f"{identifier}-{version}-{url}",
                grant=DeviceCodeGrant(
                    identifier=identifier,
                    version=version,
                    discovery=StaticDiscovery(base_url=url),
                ),
            )
        ),
        herre=Herre(
            grant=HerreCacheGrant(
                cache_file=f"{identifier}-{version}_herre_cache.json",
                hash=f"{identifier}-{version}-{url}",
                grant=RefreshGrant(grant=FaktsGrant()),
            ),
        ),
    )
