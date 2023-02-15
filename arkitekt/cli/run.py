from importlib import import_module
from typing import Type
from arkitekt import Arkitekt





module_path = f"hu"

z = locals()
y = locals()


def import_builder(module_path, function_name) -> Type[Arkitekt]:
    module = import_module(module_path)
    function = getattr(module, function_name)
    return function


async def run_app(entrypoint, app):
    try:
        import_module(entrypoint)
    except ModuleNotFoundError as e:
        print(f"Could not find entrypoint module {entrypoint}")
        raise e

    async with app:
        await app.rekuest.run()

async def run_costum(entrypoint, identifier, version,   builder: str = "arkitekt.builders.easy"):

    module_path, function_name = builder.rsplit(".", 1)
    builder = import_builder(module_path, function_name)



    app = builder(identifier, version)

    await run_app(entrypoint, app)



async def run_easy(entrypoint, identifier, version, url, public_url, instance_id):
    from arkitekt.builders import easy

    app = easy(identifier, version, url, instance_id=instance_id)


    await run_app(entrypoint, app)



async def run_port(entrypoint, identifier, version, url, token):
    from arkitekt.builders import port

    app = port(identifier, version, url=url, token=token)


    await run_app(entrypoint, app)    
    







