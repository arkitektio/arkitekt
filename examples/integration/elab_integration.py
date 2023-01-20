from pydantic import BaseModel
from flabby.app import ConnectedApp
from flabby.resti import Resti


x = ConnectedApp(
    resti=Resti(
        endpoint_url="https://localhost:443/api/v1",
        token="220a2ca06f83766b099c52f69e961a54883cb3b118623bed2b11808b354f8021e70f91a0157fea854abd",
    )
)


class LabExperiment(BaseModel):
    id: str


async def get_lab_experiment(id: str) -> LabExperiment:
    return await x.resti.post("/experiments", {"id": id})


x.rekuest.structure_registry.register_as_structure(
    LabExperiment, "@labby/experiment", expand=get_lab_experiment
)


@x.arkitekt.register()
async def create_lab_experiment() -> LabExperiment:
    """Create a lab experiment

    Creates a new experiment on a elabftw server.

    Returns:
        LabExperiment: The created experiment
    """
    response = await x.resti.post("/experiments")
    return LabExperiment(id=response.data["id"])


with x:
    x.arkitekt.run()
