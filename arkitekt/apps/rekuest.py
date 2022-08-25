from arkitekt.apps.herre import HerreApp
from pydantic import Field
from rekuest.rekuest import Rekuest


class RekuestApp(HerreApp):
    """Mikro App

    It is responsible for setting up the connection to the mikro-server and
    handling authentification and setting up the configuration. Mikro handles the creation of the datalayer and
    the graphql client.

    You can compose this app together with other apps to create a full fledged app. (Like combining with
    arkitekt to enable to call functions that you define on the app). See the example in the docstring.

    Attributes:
        fakts (Fakts): The fakts instance to use.
        mikro (Mikro): The mikro instance to use.
        herre (Herre): The herre instance to use.

    """

    rekuest: Rekuest = Field(default_factory=Rekuest)
    """The mikro layer that is used for the datalayer and
    api client
    """
