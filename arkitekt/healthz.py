from ssl import SSLContext
import ssl
from typing import Optional

import aiohttp
import certifi
from pydantic import Field
from koil.composition import KoiledModel
from fakts.fakts import Fakts


class FaktsHealthz(KoiledModel):
    """A model to check the healthz endpoint on a service configured through fakts."""

    fakts: Fakts = Field(
        description="The Fakts instance to use to fetch the healthz endpoint"
    )
    fakts_group: str = Field(
        description="The Fakts group to use to fetch the healthz endpoint"
    )
    ssl_context: SSLContext = Field(
        default_factory=lambda: ssl.create_default_context(cafile=certifi.where()),
        description="SSL Context to use for the request",
    )

    healthz_item: str = Field(
        default="healthz",
        description="The item in the Fakts group that contains the healthz endpoint. Fakts->Group->Item",
    )
    strict: bool = Field(
        default=False,
        description="Whether to raise an exception if the healthz endpoint is not working",
    )
    endpoint_url: Optional[str] = Field(description="Overwrite the endpoint url.")

    async def check(self):
        """Check the healthz endpoint of the Fakts instance."""
        self.endpoint_url = await self.fakts.aget(self.fakts_group)[self.healthz_item]

        async with aiohttp.ClientSession(
            headers={"Content-Type": "application/json"},
            connector=aiohttp.TCPConnector(ssl=self.ssl_context),
        ) as session:
            # get json from endpoint
            async with session.get(self.endpoint_url + "?format=json") as resp:
                healthz_json = await resp.json()
                if self.strict:
                    # check if all services are working
                    faulty_services = []
                    for key, value in healthz_json.items():
                        if value != "working":
                            faulty_services.append({"service": key, "error": value})

                    if faulty_services:
                        raise Exception(f"Faulty services: {faulty_services}")

                if "detail" in healthz_json:
                    # detail is only present if the endpoint is not working
                    raise Exception("Error on the Healtzh endpoint ")

                return healthz_json

    class Config:
        underscore_attrs_are_private = True
