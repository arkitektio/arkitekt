from fakts.fakts import Fakts
from fakts.grants.yaml import YamlGrant
from herre import Herre
from arkitekt import ause




async def test_expanding():
    facts = Fakts(grants=[YamlGrant(filepath="tests/configs/bergen.yaml")])


    node = await ause(package="hahahaha", interface="karl")
    assert node.name == "Karl"