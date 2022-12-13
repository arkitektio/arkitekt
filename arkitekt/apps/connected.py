from arkitekt.apps.mikro import MikroApp
from arkitekt.apps.rekuest import RekuestApp
from arkitekt.apps.unlok import UnlokApp


class ConnectedApp(MikroApp, RekuestApp, UnlokApp):
    pass


class App(ConnectedApp):
    pass
