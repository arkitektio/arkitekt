from ssl import SSLContext
import ssl
from typing import Any, Dict, Optional

import aiohttp
import certifi
from pydantic import Field
from koil.composition import KoiledModel
from fakts.fakt.base import Fakt
from fakts.fakts import get_current_fakts


class HealthzConfig(Fakt):
    healthz: str


class FaktsHealthz(KoiledModel):
    ssl_context: SSLContext = Field(
        default_factory=lambda: ssl.create_default_context(cafile=certifi.where())
    )
    fakts_group: str
    strict: bool = False
    endpoint_url: Optional[str]
    fakt: Optional[HealthzConfig]

    _old_fakt: Dict[str, Any] = None

    def configure(self, config: HealthzConfig):
        self.endpoint_url = config.healthz

    async def check(self):
        fakts = get_current_fakts()

        if fakts.has_changed(self._old_fakt, self.fakts_group):
            self._old_fakt = await fakts.aget(self.fakts_group)
            self.configure(HealthzConfig(**self._old_fakt))

        async with aiohttp.ClientSession(
            headers={"Content-Type": "application/json"},
            connector=aiohttp.TCPConnector(ssl=self.ssl_context),
        ) as session:
            # get json from endpoint
            async with session.get(self.endpoint_url + "?format=json") as resp:

                healthz_json = await resp.json()
                if self.strict:
                    faulty_services = []
                    for key, value in healthz_json.items():
                        if value != "working":
                            faulty_services.append({"service": key, "error": value})

                    if faulty_services:
                        raise Exception(f"Faulty services: {faulty_services}")

                if "detail" in healthz_json:
                    raise Exception("Error on the Healtzh endpoint ")

                return healthz_json

    class Config:
        underscore_attrs_are_private = True
