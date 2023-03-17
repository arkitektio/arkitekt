from importlib import import_module
from arkitekt.utils import create_arkitekt_folder
from pydantic import BaseModel, Field


try:
    from rekuest.api.schema import DefinitionInput
    from rekuest.definition.registry import get_default_definition_registry
except ImportError as e:
    raise ImportError("Please install rekuest to use this feature") from e

    
import os
from typing import List
import yaml
import json
import datetime

def import_deployer(builder):
    module_path, function_name = builder.rsplit(".", 1)
    module = import_module(module_path)
    function = getattr(module, function_name)
    return function

def generate_definitions(module_path) -> List[DefinitionInput]:

    import_module(module_path)
    reg = get_default_definition_registry()
    return list(reg.definitions.keys())


class Deployment(BaseModel):
    identifier: str
    version: str
    deployer: str = "arkitekt.deployers.port.dockerbuild"
    builder: str
    definitions: List[DefinitionInput]
    scopes: List[str] = []
    deployed: dict
    deployed_at: datetime.datetime = Field(default_factory=datetime.datetime.now)


class ConfigFile(BaseModel):
    deployments: List[Deployment] = []
    latest_deployment: datetime.datetime = Field(default_factory=datetime.datetime.now)







def generate_deployment(identifier: str, version: str, module_path: str, deployed: dict, deployer: str,  scopes: List[str], with_definitions = True, builder: str = "arkitekt.builders.port") -> Deployment:

    path = create_arkitekt_folder()


    config_file = os.path.join(path, "deployments.yaml")

    definitions = generate_definitions(module_path) if with_definitions else []

    deployment = Deployment(identifier=identifier, version=version, deployer=deployer, definitions=definitions, deployed=deployed, scopes=scopes, builder=builder)



    if os.path.exists(config_file):
        with open(config_file, "r") as file:
            config = ConfigFile(**yaml.safe_load(file))
            for existing_deployment in config.deployments:
                if existing_deployment.identifier == identifier and existing_deployment.version == version:
                    raise FileExistsError(f"This deployment already exists: {identifier}:{version}. Please upgrade your version number.")

            config.deployments.append(deployment)
            config.latest_deployment = datetime.datetime.now()
    else:
        config = ConfigFile(deployments=[deployment])

    with open(config_file, "w") as file:
        yaml.safe_dump(json.loads(config.json(exclude_none=True, exclude_unset=True)), file, sort_keys=True)



