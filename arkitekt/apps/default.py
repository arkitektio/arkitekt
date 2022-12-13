from arkitekt.apps.connected import ConnectedApp


class Arkitekt(ConnectedApp):
    """Arkitekt

    An app that connected to the services of the arkitekt Api,
    it comes included with the following services:

    - Rekuest: A service for that handles requests to the arkitekt Api as well as provides an
      interface to provide functionality on the arkitekt Api.
    - Herre: A service for that handles the authentication and authorization of the user
    - Fakts: A service for that handles the discovery
      and retrieval of the configuration of the arkitekt Api
    - Mikro: A service for that handles the storage and data of microscopy data

    Apps have to be always used within a context manager, this is to ensure that the services
    are properly closed when the app is no longer needed.

    Example:
        >>> from arkitekt import Arkitekt
        >>> app = Arkitekt()
        >>> with app:
        >>>     # Do stuff
        >>> # App is closed



    """
