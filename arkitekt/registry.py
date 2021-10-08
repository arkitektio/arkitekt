
CURRENT_RPC = None
CURRENT_AGENT = None


def get_current_postman(force_creation=True, **kwargs):
    global CURRENT_RPC
    if CURRENT_RPC is None and force_creation:
        from arkitekt.postman import Postman
        CURRENT_RPC = Postman(**kwargs)
    return CURRENT_RPC



def set_current_rpc(arkitekt, overwrite=False):
    global CURRENT_RPC
    CURRENT_RPC = arkitekt


def get_current_agent(force_creation=True, **kwargs):
    global CURRENT_AGENT
    if CURRENT_AGENT is None and force_creation:
        from arkitekt.agents import AppAgent
        CURRENT_AGENT = AppAgent( **kwargs)
    return CURRENT_AGENT


def set_current_agent(arkitekt, overwrite=False):
    global CURRENT_AGENT
    CURRENT_AGENT = arkitekt