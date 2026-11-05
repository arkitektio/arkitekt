"""``pip install arkitekt``, in a container of its own, reaches a hub's services over its mesh.

The mesh node is one of arkitekt's own dependencies (behind a platform marker), not an
extra. This is the test that the install, the default mesh mode and a real login fit:

- the hub is konstruktor's, with a mesh of its own (``mesh=True``): each service is
  advertised at loopback, on the hub's docker network, and on the mesh;
- the app is the arkitekt wheel built from this checkout, installed with no extras into
  a container on a network of its own. It reaches the hub only at the host's published
  ports: loopback is the container itself, and the hub's network is not its network;
- it logs in with a mandate key at the gateway, leaves ``ARKITEKT_MESH`` unset (the
  default, ``auto``), and calls mikro, which only the mesh leads to.

Needs Docker, ``konstruktor`` and ``mikro``. Its own workflow runs it
(``.github/workflows/mesh.yaml``); locally: ``uv run pytest tests/mesh -m mesh -rs``.
"""

from __future__ import annotations

import json
import os
import secrets
import shutil
import subprocess
from collections.abc import Iterator
from pathlib import Path
from urllib.parse import urlparse

import pytest

pytestmark = [pytest.mark.mesh, pytest.mark.needs_docker]

konstruktor = pytest.importorskip("konstruktor", reason="builds the hub the app logs in to")
pytest.importorskip("mikro", reason="the service the app calls")

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).parent
APP = "mesh-install-test"


def docker(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    """Run the docker CLI, capturing what it says."""
    return subprocess.run(["docker", *args], capture_output=True, text=True, check=check)


@pytest.fixture(scope="module")
def hub() -> Iterator[konstruktor.Hub]:
    """mikro, on a hub with a mesh of its own."""
    from mikro import mikro_service

    with konstruktor.testing_hub(
        name="meshhub", service_images=[mikro_service.image], mandate_keys=1, mesh=True
    ) as hub:
        hub.up()
        hub.wait_ready()
        yield hub


@pytest.fixture(scope="module")
def client_image(tmp_path_factory: pytest.TempPathFactory) -> Iterator[str]:
    """The app's image: this checkout's wheel, installed as a user would."""
    context = tmp_path_factory.mktemp("mesh-client")
    # A shallow checkout has no tags for hatch-vcs to read a version from.
    env = {**os.environ, "SETUPTOOLS_SCM_PRETEND_VERSION": "0.0.0"}
    subprocess.run(
        ["uv", "build", "--wheel", "--out-dir", str(context / "wheels"), str(ROOT)],
        check=True,
        env=env,
        capture_output=True,
    )
    for name in ("Dockerfile", "client.py"):
        shutil.copy(HERE / name, context / name)

    tag = f"arkitekt-mesh-install-test:{secrets.token_hex(4)}"
    build = docker("build", "--quiet", "--tag", tag, str(context), check=False)
    assert build.returncode == 0, build.stderr
    yield tag
    docker("image", "rm", "--force", tag, check=False)


@pytest.fixture
def own_network() -> Iterator[str]:
    """A docker network of the app's own: not the hub's."""
    name = f"arkitekt-mesh-install-{secrets.token_hex(4)}"
    docker("network", "create", name)
    yield name
    docker("network", "rm", name, check=False)


def test_an_app_installed_without_extras_reaches_a_service_only_over_the_mesh(
    hub: konstruktor.Hub, client_image: str, own_network: str
) -> None:
    """Logged in at the gateway, the app calls mikro through the one route it has: the mesh."""
    mesh = hub.mesh
    assert mesh is not None, "the hub was made with a mesh, and says of none"
    # The address the mesh is published at is one this machine and its containers
    # both reach; the gateway is published there too.
    address = urlparse(mesh.coord_url).hostname
    port = urlparse(hub.gateway_url).port

    run = docker(
        "run",
        "--rm",
        "--network",
        own_network,
        "--volume",
        f"{mesh.ca_file}:/mesh/ca.pem:ro",
        "--env",
        f"FAKTS_URL=http://{address}:{port}",
        "--env",
        f"FAKTS_MANDATE_KEY={hub.mandate_key(APP)}",
        # The gateway is plain HTTP, at an address that is not loopback.
        "--env",
        "FAKTS_ALLOW_INSECURE_TRANSPORT=1",
        "--env",
        "ARKITEKT_MESH_CA_FILE=/mesh/ca.pem",
        # A container's id is otherwise its device id, and a new login each run.
        "--env",
        f"ARKITEKT_DEVICE_ID={APP}",
        client_image,
        check=False,
    )
    if run.returncode != 0:
        logs = hub.logs(tail=60).stdout
        pytest.fail(f"the app failed:\n{run.stdout}\n{run.stderr}\n--- hub ---\n{logs}")

    said = json.loads(run.stdout.strip().splitlines()[-1])
    assert said["folder"]
    # Over the mesh: the only alias that leads anywhere from that container.
    assert said["kind"] == "mesh"
    assert said["proxy"]
