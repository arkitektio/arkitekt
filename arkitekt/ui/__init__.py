from arkitekt.schema import Node
from koil.loop import koil
from koil import get_current_koil

def ui(node: Node, *args, **kwargs):
    assert get_current_koil().state.threaded, "cannot do this in a an event loop thingy ding"
    raise NotImplementedError("Needs to be implemented Again")