"""Which device a run happens on.

A run writes it into its manifest, so the server can tell two runs of one app
on two machines apart. ``ARKITEKT_DEVICE_ID`` wins; then the machine's own id;
then one made up once and kept in the user's config directory.
"""

import logging
import os
import uuid

from machineid import id
from platformdirs import user_config_dir

from arkitekt.constants import APP_AUTHOR, APP_NAME

logger = logging.getLogger(__name__)


def get_or_set_device_id() -> str | None:
    """This device's id: from the environment, the machine, or a kept file.

    Returns:
        The id, or ``None`` if none of the three sources worked.
    """
    device_id = os.getenv("ARKITEKT_DEVICE_ID")
    if device_id:
        return device_id

    try:
        return id()
    except Exception as e:  # noqa: BLE001, any failure means "no machine id here"
        logger.warning(f"Could not get the machine id from the os: {e}")

    try:
        # This is the last resort: make a random id and keep it in the user's config dir.
        # Todo: check if we really want to do this?
        config_dir = user_config_dir(APP_NAME, APP_AUTHOR)
        device_id_file = os.path.join(config_dir, "device_id.txt")
        os.makedirs(config_dir, exist_ok=True)
        if os.path.exists(device_id_file):
            with open(device_id_file) as f:
                return f.read().strip()
        device_id = str(uuid.uuid4())
        with open(device_id_file, "w") as f:
            f.write(device_id)
        return device_id
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Could not get or keep a device id in the user directory: {e}")
        return None
