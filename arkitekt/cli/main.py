import argparse
import asyncio
import os
import sys
from enum import Enum

from rich.console import Console
from rich.prompt import Confirm, Prompt
from rich.table import Table

from arkitekt.apps.connected import App
from arkitekt.cli.prod.check import check_app, check_app_loop, check_fakts_loop
from arkitekt.cli.prod.dump import import_directory_and_dump
from arkitekt.cli.prod.run import import_directory_and_start
from fakts import Fakts
from fakts.discovery.advertised import AdvertisedDiscovery
from fakts.discovery.static import StaticDiscovery
from fakts.grants.remote.device_code import DeviceCodeGrant
from fakts.grants.remote.static import StaticGrant
from herre import Herre
from arkitekt.cli.logic.initialize import initialize_manifest
from arkitekt.cli.logic.connect import connect
from arkitekt.cli.logic.run import run
from arkitekt.cli.logic.dev import dev
from arkitekt.cli.logic.build import build
import yaml


try:
    from rich.traceback import install

    install()
except:
    pass

directory = os.getcwd()


class ArkitektOptions(str, Enum):
    INIT = "init"
    CONNECT = "connect"
    RUN = "run"
    WAIT = "wait"
    DEV = "dev"
    DUMP = "dump"
    BUILD = "build"


class TemplateOptions(str, Enum):
    AGENT = "agent"
    CLIENT = "client"


class GrantOptions(str, Enum):
    CLAIM = "claim"
    DEVICE = "device"


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
    claim=False,
    silent=False,
    overwrite=False,
    token=None,
    endpoint_url=None,
    retries=3,
    interval=1,
    tag=None,
    grant=GrantOptions.DEVICE,
):

    console = Console()
    console.print(HEADER)

    try:

        if path == ".":
            app_directory = os.getcwd()
            name = name or os.path.basename(app_directory)
        else:
            app_directory = os.path.join(os.getcwd(), path)
            name = name or path

        run_script_path = os.path.join(app_directory, "run.py")
        config_path = os.path.join(app_directory, ".arkitekt")

        if script == ArkitektOptions.INIT:
            initialize_manifest(app_directory=app_directory, silent=silent)
            return

        if script == ArkitektOptions.CONNECT:
            connect(app_directory=app_directory, silent=silent)
            return

        if script == ArkitektOptions.RUN:
            run(path=path, silent=silent, token=token, endpoint=endpoint_url)
            return

        if script == ArkitektOptions.DEV:
            dev(path=path, silent=silent, token=token, endpoint=endpoint_url)
            return

        if script == ArkitektOptions.BUILD:
            build(path=path, silent=silent, tag=tag)
            return

        if script == ArkitektOptions.WAIT:

            url = endpoint_url or (
                Prompt.ask(
                    "Give us the path to your fakts instance",
                    default=os.getenv("FAKTS_ENDPOINT_URL", "http://localhost:8000/f/"),
                )
                if not silent
                else os.getenv("FAKTS_ENDPOINT_URL", "http://localhost:8000/f/")
            )
            answer = asyncio.run(
                check_fakts_loop(
                    console,
                    endpoint_url=url,
                    retries=retries,
                    interval=interval,
                )
            )
            if answer:
                console.print("Fakts is up and running")
            return

        if script == ArkitektOptions.DEV:

            from arkitekt.cli.dev.autostage import watch_directory_and_stage

            if not os.path.isfile(run_script_path):
                console.print(
                    f"Could't find a run.py in {app_directory} {run_script_path}"
                )
                return
            if not os.path.isfile(fakts_path):
                console.print(f"{app_directory} does not have a valid fakts.yaml")
                return

            asyncio.run(watch_directory_and_stage(path, entrypoint="run"))

        if script == ArkitektOptions.RUN:

            if not os.path.isfile(run_script_path):
                console.print(
                    f"Could't find a run.py in {app_directory} {run_script_path}"
                )
                return
            if not os.path.isfile(fakts_path):
                console.print(f"{app_directory} does not have a valid fakts.yaml")
                return

            asyncio.run(import_directory_and_start(path, entrypoint="run"))

        if script == ArkitektOptions.DUMP:

            if not os.path.isfile(run_script_path):
                console.print(
                    f"Could't find a run.py in {app_directory} {run_script_path}"
                )
                return
            if not os.path.isfile(fakts_path):
                console.print(f"{app_directory} does not have a valid fakts.yaml")
                return

            asyncio.run(import_directory_and_dump(path, entrypoint="run"))

        if script == ArkitektOptions.CHECK:

            if not os.path.isfile(fakts_path):
                console.print(
                    f"Directory does not containt a valid fakts.yaml. Please initialize through 'arkitekt init {path}' first"
                )
                return

            fakts = Fakts(fakts_path=fakts_path)
            if not fakts.loaded_fakts:
                console.print(
                    f"Configuration in fakts.yaml is not sufficient please reinitilize through 'arkitekt init {path}'"
                )

            app = App(fakts=fakts)
            state = asyncio.run(
                check_app_loop(
                    console,
                    app,
                    retries=retries,
                    interval=interval,
                )
            )

            table = Table(title="App State")

            table.add_column("Service")
            table.add_column("Subservice")
            table.add_column("Message")

            for service, subservices in state.items():
                for subservice, status in subservices.items():
                    table.add_row(service, subservice, status)

            console.print(table)

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
                    initialize_fakts = (
                        Confirm.ask("Do you want to refresh the Apps configuration? ")
                        if not silent
                        else False
                    )
                    if not initialize_fakts:
                        console.print(f"Nothing done. Bye :smiley: ")
                        return
                else:
                    initialize_fakts = refresh

            if initialize_fakts:

                console.print(f"Initializing a new Configuration for {name}")

                app_identifier = (
                    name if silent else Prompt.ask("Give your app a unique identifier")
                )
                app_version = (
                    "0.0.1" if silent else Prompt.ask("Give your app a version")
                )
                app_description = (
                    "A new app" if silent else Prompt.ask("Give your app a description")
                )

                console.log("Which scopes do you want your app to have?")
                scopes = []
                for scope in available_scopes:
                    if Confirm.ask(f"App should have {scope} scope?"):
                        scopes.append(scope)

                if not scopes:
                    console.print("App needs at least one scope")
                    return

                manifest = {
                    "identifier": app_identifier,
                    "version": app_version,
                    "description": app_description,
                    "scopes": scopes,
                }

                with open(fakts_path, "w") as f:
                    yaml.dump(manifest, f)

                if scan_network is None:
                    scan_network = (
                        Confirm.ask(
                            "Do you want to automatically scan the network for local instances?"
                        )
                        if not silent
                        else False
                    )

                    if scan_network:
                        discovery = AdvertisedDiscovery()
                    else:
                        url = endpoint_url or (
                            Prompt.ask(
                                "Give us the path to your fakts instance",
                                default=os.getenv(
                                    "FAKTS_ENDPOINT_URL", "http://localhost:8000/f/"
                                ),
                            )
                            if not silent
                            else os.getenv(
                                "FAKTS_ENDPOINT_URL", "http://localhost:8000/f/"
                            )
                        )
                        discovery = StaticDiscovery(base_url=url)

                    if grant == GrantOptions.CLAIM:
                        console.print(f"Initializing through claiming process")
                        client_id = client_id or os.getenv("FAKTS_CLIENT_ID", None)
                        client_secret = client_secret or os.getenv(
                            "FAKTS_CLIENT_SECRET", None
                        )

                        assert (
                            client_id and client_secret
                        ), "Please provide a client id and secret or set FAKTS_CLIENT_ID and FAKTS_CLIENT_SECRET as env variables"

                        fakts = Fakts(
                            grant=ClaimGrant(
                                discovery=discovery,
                                client_id=client_id,
                                client_secret=client_secret,
                            ),
                        )

                    elif grant == GrantOptions.DEVICE:
                        console.print(f"Initializing through device code")
                        has_webrowser = (
                            Confirm.ask(
                                "Do you have a webbrowser installed? Otherwise we will generate a code that you need to enter manually"
                            )
                            if not silent
                            else False
                        )

                        fakts = Fakts(
                            grant=DeviceCodeGrant(
                                discovery=discovery, open_browser=has_webrowser
                            ),
                            fakts_path=fakts_path,
                            force_refresh=True,
                        )

                    else:
                        raise NotImplementedError("Grant type not implemented")

                    with fakts as f:
                        f.load()

            save_run = True
            if os.path.isfile(run_script_path):
                save_run = refresh or (
                    Confirm.ask(
                        "run.py already exists? Do you want to overwrite the run.py file? :smiley: "
                    )
                    if not silent
                    else False
                )

            if save_run:
                console.print("Initializing Templates for the App")
                if not template:
                    template = (
                        Prompt.ask(
                            "Which Template do you want to use?",
                            choices=list(template_map.keys()),
                            default="agent",
                        )
                        if not silent
                        else "agent"
                    )

                with open(run_script_path, "w") as f:
                    f.write(template_map[template])
                    console.print("Create new Entrypoint for this App")

    except:
        console.print_exception()
        sys.exit(1)


def entrypoint():
    parser = argparse.ArgumentParser(description="Say hello")
    parser.add_argument("script", type=ArkitektOptions, help="The Script Type")
    parser.add_argument("path", type=str, help="The Path", nargs="?", default=".")
    parser.add_argument("--name", type=str, help="The Name of this script")
    parser.add_argument(
        "--retries", type=int, help="The Name of this script", default=0
    )
    parser.add_argument(
        "-t", type=str, help="The tag of the dockercontainer", default=None
    )
    parser.add_argument(
        "--interval", type=int, help="The Name of this script", default=5
    )
    parser.add_argument("--scan-network", type=bool, help="Do you want to refresh")
    parser.add_argument("--beacon", type=str, help="The adress of the beacon")
    parser.add_argument(
        "--template", type=TemplateOptions, help="The run script template"
    )
    parser.add_argument(
        "--token",
        type=str,
        help="The token to negoatite the connection",
    )
    parser.add_argument(
        "--endpoint_url",
        type=str,
        help="The endpoint url for the fakts instance",
    )
    parser.add_argument(
        "--grant", type=GrantOptions, help="The grant to use", default="device"
    )
    parser.add_argument("--silent", dest="silent", action="store_true")
    parser.add_argument("--refresh", dest="refresh", action="store_true")
    parser.add_argument(
        "--services",
        type=str,
        help="The services you want to connect to (seperated by ,)",
    )
    parser.set_defaults(silent=False)
    parser.set_defaults(refresh=False)
    parser.set_defaults(claim=False)

    args = parser.parse_args()
    print(args.silent)

    main(
        script=args.script,
        path=args.path,
        name=args.name,
        refresh=args.refresh,
        scan_network=args.scan_network,
        template=args.template,
        services=args.services.split(",") if args.services else [],
        silent=args.silent,
        token=args.token,
        tag=args.t,
        endpoint_url=args.endpoint_url,
        grant=args.grant,
        retries=args.retries,
        interval=args.interval,
    )


if __name__ == "__main__":
    entrypoint()
