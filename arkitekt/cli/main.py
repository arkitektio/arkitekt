import argparse
from enum import Enum
from arkitekt.cli.prod.run import import_directory_and_start
from fakts import Fakts
from fakts.discovery.static import StaticDiscovery
from herre import Herre
from rich.console import Console
from rich.prompt import Prompt, Confirm
import os
import asyncio

try:
    from rich.traceback import install

    install()
except:
    pass

directory = os.getcwd()


class ArkitektOptions(str, Enum):
    INIT = "init"
    DEV = "dev"
    LOGOUT = "logout"
    LOGIN = "login"
    RUN = "run"
    WAIT = "wait"


agent_script = f'''
from arkitekt import register

@register()
def test_show(name: str)-> str:
    """Demo Node

    This demo node will just pass through
    a name 

    Args:
        name (str): The name

    Returns:
        str: The pass throughed Name
    """
    return name


'''

mikro_script = f"""
from arkitekt import Arkitekt

app = Arkitekt()

with app:
    # Implement your logig here
"""

HEADER = """
                __    _  __         __    __ 
  ____ _ _____ / /__ (_)/ /_ ___   / /__ / /_
 / __ `// ___// //_// // __// _ \ / //_// __/
/ /_/ // /   / ,<  / // /_ /  __// ,<  / /_  
\__,_//_/   /_/|_|/_/ \__/ \___//_/|_| \__/  
                                             
"""


template_map = {"agent": agent_script, "client": mikro_script}


def main(
    script=ArkitektOptions.INIT,
    name=None,
    path=".",
    refresh=False,
    scan_network=None,
    beacon=None,
    template=None,
    services=[],
):

    console = Console()
    console.print(HEADER)

    if path == ".":
        app_directory = os.getcwd()
        name = name or os.path.basename(app_directory)
    else:
        app_directory = os.path.join(os.getcwd(), path)
        name = name or path

    fakts_path = os.path.join(app_directory, "fakts.yaml")
    run_script_path = os.path.join(app_directory, "run.py")

    if script == ArkitektOptions.DEV:

        from arkitekt.cli.dev.autostage import watch_directory_and_stage

        if not os.path.isfile(run_script_path):
            console.print(f"Could't find a run.py in {app_directory} {run_script_path}")
            return
        if not os.path.isfile(fakts_path):
            console.print(f"{app_directory} does not have a valid fakts.yaml")
            return

        asyncio.run(watch_directory_and_stage(path, entrypoint="run"))

    if script == ArkitektOptions.RUN:

        if not os.path.isfile(run_script_path):
            console.print(f"Could't find a run.py in {app_directory} {run_script_path}")
            return
        if not os.path.isfile(fakts_path):
            console.print(f"{app_directory} does not have a valid fakts.yaml")
            return

        asyncio.run(import_directory_and_start(path, entrypoint="run"))

    if script == ArkitektOptions.LOGIN:

        if not os.path.isfile(fakts_path):
            console.print(
                f"Directory does not containt a valid fakts.yaml. Please initialize through 'arkitekt init {path}' first"
            )
            return

        fakts = Fakts(grants=[], fakts_path=fakts_path)
        if not fakts.loaded:
            console.print(
                f"Configuration in fakts.yaml is not sufficient please reinitilize through 'arkitekt init {path}'"
            )

        herre = Herre(fakts=fakts)
        console.print("Loggin in")
        herre.login()

    if script == ArkitektOptions.INIT:

        if os.path.exists(app_directory):
            console.print(f"App director already existed")
        else:
            os.mkdir(app_directory)
            console.print(f"Created a new App Directory at {app_directory}")

        initialize_fakts = True
        if os.path.isfile(fakts_path):
            console.print(
                f"There seems to have been a previous app initialized at {app_directory}"
            )
            if refresh is None:
                initialize_fakts = Confirm.ask(
                    "Do you want to refresh the Apps configuration? "
                )
                if not initialize_fakts:
                    console.print(f"Nothing done. Bye :smiley: ")
                    return
            else:
                initialize_fakts = refresh

        if initialize_fakts:

            console.print(f"Initializing a new Configuration for {name}")

            if scan_network is None:
                scan_network = Confirm.ask(
                    "Do you want to automatically scan the network for local instances?"
                )
                from fakts.grants.remote.device_code import DeviceCodeGrant
                from fakts.discovery.advertised import AdvertisedDiscovery

                if scan_network:
                    discovery = AdvertisedDiscovery()
                else:
                    url = Prompt.ask(
                        "Give us the path to your fakts instance",
                        default="http://localhost:8000/f/",
                    )
                    discovery = StaticDiscovery(base_url=url)

                has_webrowser = Confirm.ask(
                    "Do you have a webbrowser installed? Otherwise we will generate a code that you need to enter manually"
                )

                fakts = Fakts(
                    grant=DeviceCodeGrant(
                        discovery=discovery, open_browser=has_webrowser
                    ),
                    fakts_path=fakts_path,
                    force_refresh=True,
                )

                with fakts as f:
                    f.load()

        save_run = True
        if os.path.isfile(run_script_path):
            console.print("Initializing Templates for the App")
            save_run = Confirm.ask(
                "run.py already exists? Do you want to overwrite the run.py file? :smiley: "
            )

        if save_run:
            if not template:
                template = Prompt.ask(
                    "Which Template do you want to use?",
                    choices=list(template_map.keys()),
                    default="agent",
                )

            with open(run_script_path, "w") as f:
                f.write(template_map[template])
                console.print("Create new Entrypoint for this App")


def entrypoint():
    parser = argparse.ArgumentParser(description="Say hello")
    parser.add_argument("script", type=ArkitektOptions, help="The Script Type")
    parser.add_argument("path", type=str, help="The Path", nargs="?", default=".")
    parser.add_argument("--name", type=str, help="The Name of this script")
    parser.add_argument("--refresh", type=bool, help="Do you want to refresh")
    parser.add_argument("--scan-network", type=bool, help="Do you want to refresh")
    parser.add_argument("--beacon", type=str, help="The adress of the beacon")
    parser.add_argument("--template", type=str, help="The run script template")
    parser.add_argument(
        "--services",
        type=str,
        help="The services you want to connect to (seperated by ,)",
    )
    args = parser.parse_args()

    main(
        script=args.script,
        path=args.path,
        name=args.name,
        refresh=args.refresh,
        scan_network=args.scan_network,
        template=args.template,
        services=args.services.split(",") if args.services else [],
    )


if __name__ == "__main__":
    entrypoint()
