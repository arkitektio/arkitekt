import asyncio
from arkitekt.apps.connected import App


async def check_app(app: App):

    async with app:
        check_futures = []
        check_keys = []

        for key, service in app:
            if hasattr(service, "healthz"):
                check_futures.append(service.healthz.check())
                check_keys.append(key)

        return dict(zip(check_keys, await asyncio.gather(*check_futures)))
