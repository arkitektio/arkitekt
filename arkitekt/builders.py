from typing import List, Optional
import logging
import os
from .utils import create_arkitekt_folder
from .model import Manifest
from arkitekt.apps.types import NextApp, EasyApp
from arkitekt.apps.easy import build_arkitekt_easy_app
from arkitekt.apps.qt import build_arkitekt_qt_app
from arkitekt.apps.fallbacks import InstallModuleException


def easy(
    identifier: str,
    version: str = "0.0.1",
    logo: Optional[str] = None,
    scopes: Optional[List[str]] = None,
    url: str = "http://localhost:8000",
    headless: bool = False,
    log_level: str = "ERROR",
    token: Optional[str] = None,
    no_cache: bool = False,
    instance_id: str = "main",
    register_reaktion: bool = True,
    strict: bool = False,
    app_kind: str = "development",
    enforce: Optional[List[str]] = None,
) -> EasyApp:
    """Creates an easy app

    A simple way to create an Arkitekt app, that will be able to connect to the
    Arkitekt server in a variety of scenarious. It should be used for most
    Arkitekt apps, as it will provide access to the most common features and
    services.

    A few things to note:
        - Easy apps will try to establish themselves a "development" apps, by default
          which means that they will be authenticated with the Arkitekt server on
          a per user basis. If you want to create a "desktop" app, which multiple users
          can use, you should set the `app_kind` to "desktop" TODO: Currently not implemented (use next app for this)
        - The Easy builder can also be used in plugin apps, and when provided with a fakts token
           will be able to connect to the Arkitekt server without any user interaction.


    Parameters
    ----------
    identifier : str
        The apps identifier (should be globally unique, see Manifest for more info)
    version : str, optional
        The version of the app, by default "0.0.1"
    logo : str, optional
        The logo of the app as a public http url, by default None
    scopes : List[str], optional
        The scopes, that this apps requires, will default to standard scopes, by default None
    url : str, optional
        The fakts server that will be used to configure this app, in a default Arkitekt deployment this
        is the address of the "Lok Service" (which provides the Fakts API), by default "http://localhost:8000"
        Will be overwritten by the FAKTS_URL environment variable
    headless : bool, optional
        Should we run in headless, mode, e.g printing necessary interaction into the console (will forexample
        stop opening browser windows), by default False
    log_level : str, optional
        The log-level to use, by default "ERROR"
    token : str, optional
        A fakts token to use, by default None
        Will be overwritten by the FAKTS_TOKEN environment variable
    no_cache : bool, optional
        Should we skip caching token, acess-token, by default False
        Attention: If this is set to True, the app will always have to be configured
        and authenticated.
    instance_id : str, optional
        The instance_id to use, by default "main"
        Can be set to a different value, if you want to run multiple intstances
        of the same app by the same user.
        Will be overwritten by the REKUEST_INSTANCE_ID environment variable
    register_reaktion : bool, optional
        Should we register the reaktion extension, by default True
        If set to False, the app will not be able to use the reaktion extension
        (which is necessary for scheduling in app` workflows from fluss)
    app_kind : str, optional
        The kind of app to create, by default "development"
        Can be set to "desktop" to create a desktop app, that can be used by multiple users.
        While this is currently not implemented, the next app will be able to do this.

    Returns
    -------
    EasyApp
        A built app, that can be used to interact with the Arkitekt server
    """

    url = os.getenv("FAKTS_URL", url)
    token = os.getenv("FAKTS_TOKEN", token)
    instance_id = os.getenv("REKUEST_INSTANCE_ID", instance_id)

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

    app = build_arkitekt_easy_app(
        manifest=manifest,
        url=url,
        no_cache=no_cache,
        headless=headless,
        instance_id=instance_id,
        token=token,
        enforce=enforce,
    )

    if register_reaktion:
        try:
            from reaktion.extension import ReaktionExtension

            app.rekuest.agent.extensions["reaktion"] = ReaktionExtension()
        except ImportError as e:
            if strict:
                raise InstallModuleException(
                    "You need to install reaktion to use the reaktion extension"
                ) from e
            else:
                logging.warning(
                    "You need to install reaktion in order to schedule workflows. You can install it with `pip install reaktion`"
                )

    return app


def next(
    identifier: str,
    version: str = "latest",
    logo: Optional[str] = None,
    scopes: Optional[List[str]] = None,
    url: str = "http://localhost:8000",
    headless: bool = False,
    log_level: str = "ERROR",
    token: Optional[str] = None,
    no_cache: bool = False,
    instance_id: str = "main",
    register_reaktion: bool = False,
    app_kind: str = "development",
) -> NextApp:
    """Creates a next app

    A simple way to create an Arkitekt Next app, Arkitekt next apps are
    development apps by default, as they will try to register themselves
    with services that are not yet available in production (such as the
    rekuest_next and mikro_next services). They represent the next generation
    of Arkitekt apps, and will be the default way to create Arkitekt apps
    in the future. From here be dragons.

    A few things to note:
        -   The Next builder closely mimics the easy builder, but will use the
            next generation of services (such as rekuest_next and mikro_next)
            and will therefore not be compatible with the current generation.

        -  Next apps will try to establish themselves a "development" apps, by default
            which means that they will be authenticated with the Arkitekt server on
            a per user basis. If you want to create a "desktop" app, which multiple users
            can use, you should set the `app_kind` to "desktop" TODO: Currently not implemented (use next app for this)
        -  The Next builder can also be used in plugin apps, and when provided with a fakts token
           will be able to connect to the Arkitekt server without any user interaction.


    Parameters
    ----------
    identifier : str
        The apps identifier (should be globally unique, see Manifest for more info)
    version : str, optional
        The version of the app, by default "0.0.1"
    logo : str, optional
        The logo of the app as a public http url, by default None
    scopes : List[str], optional
        The scopes, that this apps requires, will default to standard scopes, by default None
    url : str, optional
        The fakts server that will be used to configure this app, in a default Arkitekt deployment this
        is the address of the "Lok Service" (which provides the Fakts API), by default "http://localhost:8000"
        Will be overwritten by the FAKTS_URL environment variable
    headless : bool, optional
        Should we run in headless, mode, e.g printing necessary interaction into the console (will forexample
        stop opening browser windows), by default False
    log_level : str, optional
        The log-level to use, by default "ERROR"
    token : str, optional
        A fakts token to use, by default None
        Will be overwritten by the FAKTS_TOKEN environment variable
    no_cache : bool, optional
        Should we skip caching token, acess-token, by default False
        Attention: If this is set to True, the app will always have to be configured
        and authenticated.
    instance_id : str, optional
        The instance_id to use, by default "main"
        Can be set to a different value, if you want to run multiple intstances
        of the same app by the same user.
        Will be overwritten by the REKUEST_INSTANCE_ID environment variable
    register_reaktion : bool, optional
        Should we register the reaktion extension, by default True
        If set to False, the app will not be able to use the reaktion extension
        (which is necessary for scheduling in app` workflows from fluss)
    app_kind : str, optional
        The kind of app to create, by default "development"
        Can be set to "desktop" to create a desktop app, that can be used by multiple users.

    Returns
    -------
    NextApp
        A built app, that can be used to interact with the Arkitekt server
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
        app_kind=app_kind,
    )

    if register_reaktion:
        try:
            from reaktion.extension import ReaktionExtension

            app.rekuest.agent.extensions["reaktion"] = ReaktionExtension()
        except ImportError as e:
            raise InstallModuleException(
                "You need to install reaktion to use the reaktion extension"
            ) from e

    return app


def jupy(
    identifier: str,
    version: str = "0.0.1",
    logo: Optional[str] = None,
    scopes: Optional[List[str]] = None,
    url: str = "http://localhost:8000",
    headless: bool = False,
    log_level: str = "ERROR",
    token: Optional[str] = None,
    no_cache: bool = False,
    instance_id: str = "main",
    register_reaktion: bool = False,
    app_kind: str = "development",
):
    """Creates a Jupyter app

    A simple way to create an Arkitekt app, that will be able to connect to the
    Arkitekt server when running inside a jupyter notebook. It simply wraps the
    the easy app, and sets the allow_sync_in_async flag to True, so that the
    the app can reliably be used in jupyter notebooks (which are async by default,
    but often are used in a sync manner). Additionally, it will also auto_enter
    the app, so that you dont have to use the app in a with statement.

    Attention:
        Running Arkitekt apps in sync mode comes with a few caveats, as the
        app will be put into another thread, and when using the app without a
        a context manager (the with statement), you will have to manually
        exit the app, by calling the `app.exit()` method. Arkitekt will otherwise
        not be able to properly shut down the app, and will continue to run in
        the background (until the notebook is restarted)

        This should only be a big problem, if you want to run multiple apps
        in the same notebook, and therefore should not be necessary in most cases,
        but you should be aware of this.


    A few things to note:
        -  Jupy apps will try to establish themselves a "development" apps, by default
            which means that they will be authenticated with the Arkitekt server on
            a per user basis. If you want to create a "desktop" app, which multiple users
            can use, you should set the `app_kind` to "desktop" TODO: Currently not implemented (use next app for this)
        -  The Jupy builder can also be used in plugin apps, and when provided with a fakts token
           will be able to connect to the Arkitekt server without any user interaction.


    Parameters
    ----------
    identifier : str
        The apps identifier (should be globally unique, see Manifest for more info)
    version : str, optional
        The version of the app, by default "0.0.1"
    logo : str, optional
        The logo of the app as a public http url, by default None
    scopes : List[str], optional
        The scopes, that this apps requires, will default to standard scopes, by default None
    url : str, optional
        The fakts server that will be used to configure this app, in a default Arkitekt deployment this
        is the address of the "Lok Service" (which provides the Fakts API), by default "http://localhost:8000"
        Will be overwritten by the FAKTS_URL environment variable
    headless : bool, optional
        Should we run in headless, mode, e.g printing necessary interaction into the console (will forexample
        stop opening browser windows), by default False
    log_level : str, optional
        The log-level to use, by default "ERROR"
    token : str, optional
        A fakts token to use, by default None
        Will be overwritten by the FAKTS_TOKEN environment variable
    no_cache : bool, optional
        Should we skip caching token, acess-token, by default False
        Attention: If this is set to True, the app will always have to be configured
        and authenticated.
    instance_id : str, optional
        The instance_id to use, by default "main"
        Can be set to a different value, if you want to run multiple intstances
        of the same app by the same user.
        Will be overwritten by the REKUEST_INSTANCE_ID environment variable
    register_reaktion : bool, optional
        Should we register the reaktion extension, by default True
        If set to False, the app will not be able to use the reaktion extension
        (which is necessary for scheduling in app` workflows from fluss)
    app_kind : str, optional
        The kind of app to create, by default "development"
        Can be set to "desktop" to create a desktop app, that can be used by multiple users.

    Returns
    -------
    NextApp
        A built app, that can be used to interact with the Arkitekt server
    """
    app = easy(
        identifier=identifier,
        version=version,
        url=url,
        token=token,
        logo=logo,
        scopes=scopes,
        log_level=log_level,
        register_reaktion=register_reaktion,
        app_kind=app_kind,
        headless=headless,
        instance_id=instance_id,
        no_cache=no_cache,
    )
    app.koil.sync_in_async = True

    if register_reaktion:
        try:
            from reaktion.extension import ReaktionExtension

            app.rekuest.agent.extensions["reaktion"] = ReaktionExtension()
        except ImportError as e:
            raise InstallModuleException(
                "You need to install reaktion to use the reaktion extension"
            ) from e

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

    if not kwargs.get("token", None):
        raise ValueError("You must provide a token")

    if not kwargs.get("url", None):
        raise ValueError("You must provide a url")

    return easy(**kwargs)


def scheduler(
    identifier: str,
    version: str = "latest",
    logo: Optional[str] = None,
    scopes: Optional[List[str]] = None,
    url: str = "http://localhost:8000",
    headless: bool = False,
    log_level: str = "ERROR",
    token: Optional[str] = None,
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

    try:
        from reaktion.extension import ReaktionExtension
    except ImportError as e:
        raise ImportError(
            "You need to install reaktion to use the scheduler function"
        ) from e

    url = os.getenv("FAKTS_URL", url)
    token = os.getenv("FAKTS_TOKEN", token)

    create_arkitekt_folder(with_cache=True)

    Manifest(
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

    app = easy(
        identifier=identifier,
        version=version,
        url=url,
        token=token,
        logo=logo,
        scopes=scopes,
        log_level=log_level,
        headless=headless,
        instance_id=instance_id,
        no_cache=no_cache,
    )
    app.rekuest.agent.extensions["reaktion"] = ReaktionExtension()

    return app


def publicqt(
    identifier: str,
    version: str = "latest",
    logo: Optional[str] = None,
    scopes: Optional[List[str]] = None,
    url: str = "http://localhost:8000",
    headless: bool = False,
    log_level: str = "ERROR",
    token: Optional[str] = None,
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
    try:
        from reaktion.extension import ReaktionExtension
    except ImportError as e:
        raise ImportError(
            "You need to install reaktion to use the scheduler function"
        ) from e

    manifest = Manifest(
        version=version,
        identifier=identifier,
        scopes=scopes + ["openid"]
        if scopes
        else ["openid"],  # we need openid to get the user info
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
    app.rekuest.agent.extensions["reaktion"] = ReaktionExtension()
    app.enter()
    return app
