from arkitekt.apps.mikro import MikroApp
from arkitekt.apps.rekuest import RekuestApp
from arkitekt.apps.unlok import UnlokApp
from typing import Optional


class ConnectedApp(MikroApp, RekuestApp, UnlokApp):
    title: Optional[str]
    version: Optional[str]
    pass

    def _repr_html_(self):
        return (
            f'''<div><h4>{self.title or 'Arkitekt App'} {f"@{self.version}" if self.version else ""}</h4><table>'''
            + "\n".join(["<tr><td>{}</td><td>{}</td></tr>".format(key, value._repr_html_inline_()) for key, value in self if hasattr(value, "_repr_html_inline_")])
            + "</table></div>"
        )


class App(ConnectedApp):
    pass
