from typing import List, Optional
import logging
import os
from .utils import create_arkitekt_folder
from .model import Manifest


def easy(
    identifier: str,
    version: str = "latest",
    logo: str = None,
    scopes: List[str] = None,
    url: str = "http://localhost:8000",
    headless: bool = False,
    log_level: str = "ERROR",
    token: str = None,
    no_cache: bool = False,
    instance_id: str = "main",
):
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
    from arkitekt.apps.default import App, build_arkitekt_app

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

    app = build_arkitekt_app(
        manifest=manifest,
        url=url,
        no_cache=no_cache,
        headless=headless,
        instance_id=instance_id,
        token=token,
    )

    try:
        from reaktion.extension import ReaktionExtension

        app.rekuest.agent.extensions["reaktion"] = ReaktionExtension()
    except ImportError:
        pass

    return app


def next(
    identifier: str,
    version: str = "latest",
    logo: str = None,
    scopes: List[str] = None,
    url: str = "http://localhost:8000",
    headless: bool = False,
    log_level: str = "ERROR",
    token: str = None,
    no_cache: bool = False,
    instance_id: str = "main",
):
    """Next app creation

    A simple way to create an Arkitekt app with a device code grant and
    all new features enabled. This will currently replace the
    mikro service with a new one that supports new features, requires
    the mikro_next package to be installed.


    Args:
        identifier (str): The apps identifier
        version (str, optional): The apps verion. Defaults to "latest".
        url (_type_, optional): The app configuration url. Defaults to "http://localhost:8000/f/".
        headless (bool, optional): Do not open a browser window. Defaults to False.
        allow_sync_in_async (bool, optional): Should we allow the creation of a sync interface in an async loop (necessary for a sync interface in jupyter). Defaults to True.

    Returns:
        Arkitekt: _description_
    """
    from arkitekt.apps.next import build_next_app

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

    app = build_next_app(
        manifest=manifest,
        url=url,
        no_cache=no_cache,
        headless=headless,
        instance_id=instance_id,
        token=token,
    )

    return app


def jupy(
    identifier: str,
    version: str = "latest",
    url: str = "http://localhost:8000",
    headless: bool = False,
    instance_id: str = "main",
    no_cache: bool = False,
):
    app = easy(
        identifier,
        version,
        url=url,
        headless=headless,
        allow_sync_in_async=True,
        log_level="ERROR",
        instance_id=instance_id,
        no_cache=no_cache,
    )
    app.koil.sync_in_async = True
    app.enter()  # This will start the event loop with the sync interface (for automatic awaits in jupyter)
    return app


def port(**kwargs):
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
    from arkitekt.apps.default import App, build_arkitekt_app

    if not kwargs.get("token", None):
        raise ValueError("You must provide a token")

    if not kwargs.get("url", None):
        raise ValueError("You must provide a url")

    return easy(**kwargs)


def scheduler(
    identifier: str,
    version: str = "latest",
    logo: str = None,
    scopes: List[str] = None,
    url: str = "http://localhost:8000",
    headless: bool = False,
    log_level: str = "ERROR",
    token: str = None,
    no_cache: bool = False,
    instance_id: str = "main",
):
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
    from arkitekt.apps.default import App, build_arkitekt_app
    from arkitekt.apps.rekuest import ArkitektWebsocketAgentTransport

    try:
        from reaktion.extension import ReaktionExtension
    except ImportError as e:
        raise ImportError(
            "You need to install reaktion to use the scheduler function"
        ) from e

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

    app = build_arkitekt_app(
        manifest=manifest,
        url=url,
        no_cache=no_cache,
        headless=headless,
        instance_id=instance_id,
    )
    app.rekuest.agent.extensions["reaktion"] = ReaktionExtension()

    return app


def publicqt(
    identifier: str,
    version: str = "latest",
    logo: str = None,
    scopes: List[str] = None,
    url: str = "http://localhost:8000",
    headless: bool = False,
    log_level: str = "ERROR",
    token: str = None,
    no_cache: bool = False,
    instance_id: str = "main",
    parent=None,
    beacon_widget=None,
    login_widget=None,
    force_herre_grant=None,
    settings=None,
):
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

    from arkitekt.apps.qt import build_arkitekt_qt_app

    manifest = Manifest(
        version=version,
        identifier=identifier,
        scopes=scopes or ["openid", "read", "write"],
        logo=logo,
    )

    create_arkitekt_folder(with_cache=True)

    try:
        from rich.logging import RichHandler

        logging.basicConfig(level=log_level, handlers=[RichHandler()])
    except ImportError:
        logging.basicConfig(level=log_level)

    app = build_arkitekt_qt_app(
        manifest=manifest,
        parent=parent,
        no_cache=no_cache,
        beacon_widget=beacon_widget,
        login_widget=login_widget,
        instance_id=instance_id,
        settings=settings,
    )
    print("Entering", parent)
    app.enter()  # This will start the event loop and attach the event handlers
    return app


def publicscheduleqt(
    identifier: str,
    version: str = "latest",
    parent=None,
    logo: Optional[str] = None,
    scopes: Optional[List[str]] = None,
    beacon_widget=None,
    login_widget=None,
    force_herre_grant=None,
    instance_id: str = "main",
    no_cache: bool = False,
    log_level: str = "ERROR",
    settings=None,
):
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

    from arkitekt.apps.scheduleqt import build_arkitekt_scheduleqt_app

    manifest = Manifest(
        version=version,
        identifier=identifier,
        scopes=scopes or ["openid", "read", "write"],
        logo=logo,
    )

    try:
        from rich.logging import RichHandler

        logging.basicConfig(level=log_level, handlers=[RichHandler()])
    except ImportError:
        logging.basicConfig(level=log_level)

    create_arkitekt_folder(with_cache=True)

    x = build_arkitekt_scheduleqt_app(
        manifest=manifest,
        parent=parent,
        no_cache=no_cache,
        beacon_widget=beacon_widget,
        login_widget=login_widget,
        instance_id=instance_id,
        settings=settings,
    )
    x.enter()
    return x
