from arkitekt.apps.connected import App
from arkitekt.apps.rekuest import ArkitektRekuest, ArkitektAgent
from fakts.grants.remote.device_code import DeviceCodeGrant
from fakts.fakts import Fakts
from fakts.grants.remote.static import StaticGrant
from fakts.grants import CacheGrant
from herre.grants import CacheGrant as HerreCacheGrant
from herre.grants.oauth2.refresh import RefreshGrant
from herre.grants.fakts import FaktsGrant
from fakts.grants.remote import Manifest
from typing import List, Optional
from fakts.discovery.well_known import WellKnownDiscovery
from herre import Herre
import logging
from koil.composition import PedanticKoil
import os
from .utils import create_arkitekt_folder
from rekuest.contrib.fakts.websocket_agent_transport import FaktsWebsocketAgentTransport


def easy(
    identifier: str,
    version: str = "latest",
    logo: str = None,
    scopes: List[str] = None,
    url: str = "http://localhost:8000",
    headless: bool = False,
    allow_sync_in_async: bool = True,
    log_level: str = "ERROR",
    token: str = None,
    instance_id: str = "main",
) -> App:
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
    url = os.getenv("FAKTS_URL", url)
    token = os.getenv("FAKTS_TOKEN", token)

    create_arkitekt_folder(with_cache=True)

    manifest = Manifest(
        version=version,
        identifier=identifier,
        scopes=scopes if scopes else ["openid"],
        logo=logo,
    )

    try:
        from rich.logging import RichHandler

        logging.basicConfig(level=log_level, handlers=[RichHandler()])
    except ImportError:
        logging.basicConfig(level=log_level)

    return App(
        identifier=identifier,
        version=version,
        koil=PedanticKoil(sync_in_async=allow_sync_in_async),
        fakts=Fakts(
            grant=CacheGrant(
                cache_file=f".arkitekt/cache/{identifier}-{version}_cache.json",
                hash=f"{identifier}-{version}-{url}",
                grant=DeviceCodeGrant(
                    manifest=manifest,
                    open_browser=not headless,
                    discovery=WellKnownDiscovery(
                        url=url, auto_protocols=["https", "http"]
                    ),
                ),
            )
        ),
        herre=Herre(
            grant=HerreCacheGrant(
                cache_file=f".arkitekt/cache/{identifier}-{version}_herre_cache.json",
                hash=f"{identifier}-{version}-{url}",
                grant=RefreshGrant(grant=FaktsGrant()),
            ),
        ),
        rekuest=ArkitektRekuest(
            agent=ArkitektAgent(
                instance_id=instance_id,
            )
        ),
    )


def jupy(
    identifier: str,
    version: str = "latest",
    url: str = "http://localhost:8000/f/",
    headless: bool = False,
    instance_id: str = "main",
) -> App:
    app = easy(
        identifier,
        version,
        url=url,
        headless=headless,
        allow_sync_in_async=True,
        log_level="ERROR",
        instance_id=instance_id,
    )
    app.enter()
    return app


def port(
    identifier: str,
    version: str = "latest",
    url: str = "http://lok:8000",
    log_level: str = "ERROR",
    token: str = None,
    instance_id: str = "main",
) -> App:
    """Easy port creation

    A simple way to create an Arkitekt app with a device code grant
    it will cache the configuration in a file called `identifier`_token.json
    and the cache in a file called `identifier`_cache.json

    Args:
        identifier (str): The apps identifier
        version (str, optiosnal): The apps verion. Defaults to "latest".
        url (_type_, optional): The app configuration url. Defaults to "http://localhost:8000/f/".
        headless (bool, optional): Do not open a browser window. Defaults to False.
        allow_sync_in_async (bool, optional): Should we allow the creation of a sync interface in an async loop (necessary for a sync interface in jupyter). Defaults to True.

    Returns:
        Arkitekt: _description_
    """

    url = os.getenv("FAKTS_URL", url)
    token = os.getenv("FAKTS_TOKEN", token)

    if not token:
        raise ValueError("You must provide a token")

    if not url:
        raise ValueError("You must provide a url")

    create_arkitekt_folder(with_cache=True)

    try:
        from rich.logging import RichHandler

        logging.basicConfig(level=log_level, handlers=[RichHandler()])
    except ImportError:
        logging.basicConfig(level=log_level)

    return App(
        identifier=identifier,
        version=version,
        fakts=Fakts(
            grant=CacheGrant(
                cache_file=f".arkitekt/cache/{identifier}-{version}_cache.json",
                hash=f"{identifier}-{version}-{url}",
                grant=StaticGrant(token=token, discovery=WellKnownDiscovery(url=url)),
            )
        ),
        herre=Herre(
            grant=HerreCacheGrant(
                cache_file=f".arkitekt/cache/{identifier}-{version}_herre_cache.json",
                hash=f"{identifier}-{version}-{url}",
                grant=RefreshGrant(grant=FaktsGrant()),
            ),
        ),
        rekuest=ArkitektRekuest(
            agent=ArkitektAgent(
                instance_id=instance_id,
            )
        ),
    )


def scheduler(
    identifier: str,
    version: str = "latest",
    logo: str = None,
    scopes: List[str] = None,
    url: str = "http://localhost:8000",
    headless: bool = False,
    allow_sync_in_async: bool = True,
    log_level: str = "ERROR",
    token: str = None,
    instance_id: str = "main",
) -> App:
    """Scheduler app creation

    A an arkitekt scheduler app with a device code grant and a reaktion agent
    this app will be able to deploy graphs from fluss

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
        from reaktion.agent import ReaktionAgent
    except ImportError:
        raise ImportError(
            "You need to install reaktion to use the scheduler function"
        ) from None

    url = os.getenv("FAKTS_URL", url)
    token = os.getenv("FAKTS_TOKEN", token)

    create_arkitekt_folder(with_cache=True)

    manifest = Manifest(
        version=version,
        identifier=identifier,
        scopes=scopes if scopes else ["openid"],
        logo=logo,
    )

    try:
        from rich.logging import RichHandler

        logging.basicConfig(level=log_level, handlers=[RichHandler()])
    except ImportError:
        logging.basicConfig(level=log_level)

    return App(
        identifier=identifier,
        version=version,
        koil=PedanticKoil(sync_in_async=allow_sync_in_async),
        fakts=Fakts(
            grant=CacheGrant(
                cache_file=f".arkitekt/cache/{identifier}-{version}_cache.json",
                hash=f"{identifier}-{version}-{url}",
                grant=DeviceCodeGrant(
                    manifest=manifest,
                    open_browser=not headless,
                    discovery=WellKnownDiscovery(
                        url=url, auto_protocols=["https", "http"]
                    ),
                ),
            )
        ),
        herre=Herre(
            grant=HerreCacheGrant(
                cache_file=f".arkitekt/cache/{identifier}-{version}_herre_cache.json",
                hash=f"{identifier}-{version}-{url}",
                grant=RefreshGrant(grant=FaktsGrant()),
            ),
        ),
        rekuest=ArkitektRekuest(
            agent=ReaktionAgent(
                instance_id=instance_id,
                transport=FaktsWebsocketAgentTransport(fakts_group="rekuest.agent"),
            )
        ),
    )


def qt(identifier: str, version: str, parent, instance_id: str = "main") -> App:
    """
    A simple way to create an Arkitekt app within a Qt application stilll
    utilizing a device code grant to authenticate the user on an application
    level
    """

    from koil.composition.qt import QtPedanticKoil

    create_arkitekt_folder(with_cache=True)

    return App(
        identifier=identifier,
        version=version,
        koil=QtPedanticKoil(parent=parent),
        fakts=Fakts(
            grant=CacheGrant(
                cache_file=f".arkitekt/cache/{identifier}-{version}_cache.json",
                grant=DeviceCodeGrant(
                    identifier=identifier,
                    version=version,
                ),
            )
        ),
        herre=Herre(
            grant=HerreCacheGrant(
                cache_file=f".arkitekt/cache/{identifier}-{version}_herre_cache.json",
                hash=f"{identifier}-{version}",
                grant=FaktsGrant(),
            ),
        ),
        rekuest=ArkitektRekuest(
            agent=ArkitektAgent(
                instance_id=instance_id,
            )
        ),
    )


def publicqt(
    identifier: str,
    version: str = "latest",
    parent=None,
    image: Optional[str] = None,
    scopes: Optional[List[str]] = None,
    beacon_widget=None,
    login_widget=None,
    force_herre_grant=None,
    instance_id: str = "main",
) -> App:
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

    from herre.grants.fakts.fakts_login_screen import FaktsQtLoginScreen
    from herre.grants.qt.login_screen import LoginWidget
    from fakts.grants.remote.retrieve import RetrieveGrant
    from fakts.discovery.qt.selectable_beacon import (
        SelectBeaconWidget,
        QtSelectableDiscovery,
    )

    manifest = Manifest(
        version=version,
        identifier=identifier,
        scopes=scopes or ["openid", "read", "write"],
        image=image,
    )

    create_arkitekt_folder(with_cache=True)

    beacon_widget = beacon_widget or SelectBeaconWidget(parent=parent)

    login_widget = login_widget or LoginWidget(identifier, version, parent=parent)
    f = FaktsGrant(grant_class=force_herre_grant)
    print(f)
    app = App(
        identifier=identifier,
        version=version,
        fakts=Fakts(
            grant=CacheGrant(
                cache_file=f".arkitekt/cache/{identifier}-{version}_fakts_cache.json",
                grant=RetrieveGrant(
                    manifest=manifest,
                    redirect_uri="http://localhost:6767",
                    discovery=QtSelectableDiscovery(
                        widget=beacon_widget,
                        allow_appending_slash=True,
                        auto_protocols=["http", "https"],
                    ),
                ),
            ),
            assert_groups={"mikro", "rekuest"},
        ),
        herre=Herre(
            grant=HerreCacheGrant(
                cache_file=f".arkitekt/cache/{identifier}-{version}_herre_cache.json",
                hash=f"{identifier}-{version}",
                skip_cache=True,
                grant=FaktsQtLoginScreen(
                    widget=login_widget,
                    auto_login=True,
                    grant=RefreshGrant(grant=f),
                ),
            ),
        ),
        rekuest=ArkitektRekuest(
            agent=ArkitektAgent(
                instance_id=instance_id,
            )
        ),
    )

    return app
