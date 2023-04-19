from arkitekt.apps.mikro import MikroApp
from arkitekt.apps.rekuest import RekuestApp
from arkitekt.apps.unlok import UnlokApp
from arkitekt.apps.fluss import FlussApp


class ConnectedApp(MikroApp, RekuestApp, UnlokApp, FlussApp):
    identifier: str
    version: str
    pass

    def _repr_html_(self):
        return (
            f"""<div><h4>{self.identifier or 'Arkitekt App'} {f"@{self.version}" if self.version else ""}</h4><table>"""
            + "\n".join(
                [
                    "<tr><td>{}</td><td>{}</td></tr>".format(
                        key, value._repr_html_inline_()
                    )
                    for key, value in self
                    if hasattr(value, "_repr_html_inline_")
                ]
            )
            + "</table></div>"
        )


class App(ConnectedApp):
    pass
