"""The app in the sealed container: log in to the hub, call mikro, say which way it went.

Runs from the image ``tests/mesh/Dockerfile`` builds, against the environment the test
hands it (``FAKTS_URL``, ``FAKTS_MANDATE_KEY``, ``ARKITEKT_MESH_CA_FILE``). Prints one JSON
line and exits 0 when mikro answered; anything else is a failure, with its traceback.
"""

import json

# Came with arkitekt, which was installed without extras.
import arkitekt_mesh  # noqa: F401
from mikro import mikro_service

from arkitekt import easy


def main() -> None:
    """Log in, create a folder in mikro, print how it was reached."""
    setup = easy("mesh-install-test", mikro_service)
    with setup.runtime() as runtime:
        mikro = setup.resolve(runtime)
        folder = mikro.create_folder(name="over the mesh")
        # The alias the call went through: a mesh alias, carrying the node's proxy.
        alias = runtime.fakts.get_alias("mikro")
    print(json.dumps({"folder": str(folder.id), "kind": alias.kind, "proxy": alias.proxy}))


if __name__ == "__main__":
    main()
