from importlib import import_module
import asyncio
from typing import Type
from arkitekt import Arkitekt
from watchfiles import awatch
from watchfiles.filters import BaseFilter, PythonFilter
import os





def import_builder(builder) -> Type[Arkitekt]:
    module_path, function_name = builder.rsplit(".", 1)
    module = import_module(module_path)
    function = getattr(module, function_name)
    return function



async def build_and_run(builder, identifier, version, entrypoint):

    app = builder(identifier, version)

    import_module(entrypoint)

    async with app:
        await app.rekuest.run()


    

class EntrypointFilter(PythonFilter):

    def __init__(self, entrypoint, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.entrypoint = entrypoint


    def __call__(self, change, path: str) -> bool:
        x = super().__call__(change, path)
        if not x:
            return False

        x = os.path.basename(path)
        module_name = x.split(".")[0]

        return module_name == self.entrypoint



async def dev_module(identifier, version, entrypoint,  builder: str = "arkitekt.builders.easy"):


    builder_func = import_builder(builder)
    x = asyncio.create_task(build_and_run(builder_func, identifier, version, entrypoint))



    async for changes in awatch(".", watch_filter=EntrypointFilter(entrypoint), debounce=2000):
        
        print("Canceling")

        if x.done():
            print(x.exception())
            print("Restarting")

        else:
            x.cancel()
            try:
                await x;
            except asyncio.CancelledError:
                pass

        print("Restarting")
        x = asyncio.create_task(build_and_run(builder_func, identifier, version, entrypoint))


   

    
    







