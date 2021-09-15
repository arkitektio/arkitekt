from herre.auth import HerreClient
from arkitekt import ause




async def test_expanding():
    herre = HerreClient(config_path="tests/configs/bergen.yaml")

    node = await ause(package="hahahaha", interface="karl")
    assert node.name == "Karl"