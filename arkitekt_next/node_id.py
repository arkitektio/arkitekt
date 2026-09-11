import os
import uuid
from platformdirs import user_config_dir
import logging
from machineid import id

logger = logging.getLogger(__name__)

APP_AUTHOR = "arkitekt.live"
APP_NAME = "arkitekt_next"


def get_or_set_node_id() -> str | None:
    """Get or set a unique node ID for the given node name.

    Args:
        node_name (str): The name of the node.

    Returns:
        str: The unique node ID.
    """
    
    try:
        os.getenv("ARKITEKT_NODE_ID", None) 
        node_id = os.getenv("ARKITEKT_NODE_ID")
        if node_id:
            return node_id
    except Exception as e:
        logger.warning(f"Could not get ARKITEKT_NODE_ID from environment: {e}")
            
    
    try:
        return id()
    except Exception as e:
        logger.warning(f"Could not get machine ID from the os-level: {e}")

    try:
        config_dir = user_config_dir(APP_NAME, APP_AUTHOR)
        node_id_file = os.path.join(config_dir, "node_id.txt")

        if not os.path.exists(config_dir):
            os.makedirs(config_dir)

        if os.path.exists(node_id_file):
            with open(node_id_file, "r") as f:
                node_id = f.read().strip()
        else:
            node_id = str(uuid.uuid4())
            with open(node_id_file, "w") as f:
                f.write(node_id)

        return node_id

    except Exception as e:
        logger.warning(f"Could not get or set node ID in the user directory: {e}")
        return None
