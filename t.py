from arkitekt.api.schema import reserve, find
from fakts import Fakts
from herre import get_current_herre
import uuid
import time

from arkitekt.watchman import Watchman

fakts = Fakts(subapp="basic")
reference = uuid.uuid4()


node = find(package="generic", interface="center_crop")

x = reserve(node, callbacks=[f"ws:{reference}"])

w = Watchman(fakts=fakts, token_loader=get_current_herre().aget_token)
w.connect()


while True:
    time.sleep(1)
