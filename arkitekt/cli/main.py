import argparse
from enum import Enum
from fakts import Fakts
from fakts.beacon.beacon import FaktsEndpoint
from fakts.grants.beacon import BeaconGrant
from fakts.grants.endpoint_grant import EndpointGrant
from fakts.grants.prompting_beacon_grant import PromptingBeaconGrant
from fakts.grants.yaml import YamlGrant
from rich.console import Console
from rich.prompt import Prompt, Confirm
#importing the os module
import os
import namegenerator
#to get the current working directory
directory = os.getcwd()


class ArkitektOptions(str, Enum):
    INIT = "init"
    DEV = "dev"


agent_script = f"""
from arkitekt.agents.script import ScriptAgent

agent = ScriptAgent()

@agent.register()
def test_show(name: str)-> str:
    raise NotImplementedError("DD")

agent.provide()

"""

mikro_script = """
from mikro import gql

x = gql('''
myrepresentations {
    id
}
''')

"""


template_map = {
    "agent": agent_script,
    "client": mikro_script
}





def main(script = ArkitektOptions.INIT, name=None, path=".", refresh=False, scan_network=None, beacon=None, template=None):
    
    console = Console()

    if path == ".":
        app_directory = os.getcwd()
    else:
        app_directory = os.path.join(os.getcwd(),path)
        name = path


    fakts_path = os.path.join(app_directory, "fakts.yaml")
    run_script_path = os.path.join(app_directory, "run.py")


    if script == ArkitektOptions.DEV:

        import runpy
        if not os.path.isfile(run_script_path):
            console.print(f"Could't find a run.py in {app_directory} {run_script_path}")
            return
        if not os.path.isfile(fakts_path):
            console.print(f"{app_directory} does not have a valid fakts.yaml")
            return
            
        runpy.run_path(path_name=run_script_path)
 



    if script == ArkitektOptions.INIT:

        console.print("Initializing Arkitekt Started. Lets do this!")

        if os.path.exists(app_directory):
            console.print(f"App Directory already existed. No need for creation!")
        else:
            os.mkdir(app_directory)
            console.print(f"Created a new App Directory at {app_directory}")

        initialize_fakts = True
        if os.path.isfile(fakts_path):
            console.print(f"There seems to have been a previous App initialized at {app_directory}")
            if refresh is None:
                initialize_fakts = Confirm.ask("Do you want to refresh the Apps configuration? :smiley: ")
            else:
                initialize_fakts = refresh

        if initialize_fakts:

            fakt_grants = []

            console.print("---------------------------------------------")
            console.print("Initializing a new Configuration for this App")

            if scan_network is None:
                scan_network = Confirm.ask("Do you want to automatically scan the network for local instances?")
                if scan_network: fakt_grants.append(PromptingBeaconGrant())

            if scan_network is False and beacon is None:
                beacon = Prompt.ask("Give us your local beacon", default="http://localhost:3000/setupapp")
                if scan_network: fakt_grants.append(EndpointGrant(url=beacon, name="local_beacon"))

    
            fakts = Fakts(grants=fakt_grants, fakts_path=fakts_path, force_reload=refresh)

            if not fakts.loaded:
                fakts.load()

            console.print("--------------------------------------------")


        save_run = True
        if os.path.isfile(run_script_path):
            console.print("Initializing Templates for the App")
            save_run = Confirm.ask("run.py already exists? Do you want to overwrite the run.py file? :smiley: ")

        if save_run:
            if not template:
                template = Prompt.ask("Which Template do you want to use?", choices=list(template_map.keys()), default="agent")

            with open(run_script_path,"w") as f:
                f.write(template_map[template])
                console.print("Create new Entrypoint for this App")







def entrypoint():
    parser = argparse.ArgumentParser(description = 'Say hello')
    parser.add_argument('script', type=ArkitektOptions, help='The Script Type')
    parser.add_argument('path', type=str, help='The Path', nargs="?", default=".")
    parser.add_argument('--name', type=str, help='The Name of this script')
    parser.add_argument('--refresh', type=bool, help='Do you want to refresh')
    parser.add_argument('--scan-network', type=bool, help='Do you want to refresh')
    parser.add_argument('--beacon', type=str, help='The adress of the beacon')
    parser.add_argument('--template', type=str, help='The run script template')
    args = parser.parse_args()

    main(script=args.script, path=args.path, name=args.name, refresh=args.refresh, scan_network=args.scan_network, template=args.template)


if __name__ == "__main__":
    entrypoint()
