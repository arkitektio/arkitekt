"""Which mesh a run asks fakts for: passed, then the environment, then none.

arkitekt used to pass no mesh to fakts at all, so a Python app could not reach
a mesh-only service -- while the errors told users to set ARKITEKT_MESH, which
only the Rust client read.
"""

from __future__ import annotations

import pytest
from fakts import Fakts
from fakts.grants.remote import RemoteGrant
from fakts.grants.remote.authorizers.device_code import DeviceCodeAuthorizer
from fakts.mesh import MeshOptions, MeshProxy
from fakts.models import Manifest

from arkitekt.app.fakts import build_fakts, mesh_from_env
from arkitekt.app.options import ConnectionOptions

MANIFEST = Manifest(identifier="mesh-app", version="0.0.1", scopes=["openid"])
URL = "http://localhost:8000"
PROXY = "http://localhost:1055"


def asks_for_mesh_key(fakts: Fakts) -> bool:
    assert isinstance(fakts.grant, RemoteGrant)
    assert isinstance(fakts.grant.authorizer, DeviceCodeAuthorizer)
    return fakts.grant.authorizer.request_auth_key


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("ARKITEKT_MESH", "ARKITEKT_MESH_PROXY", "FAKTS_TOKEN", "FAKTS_REDEEM_TOKEN"):
        monkeypatch.delenv(name, raising=False)


@pytest.mark.parametrize("value", ["1", "true", "native", "ON "])
def test_arkitekt_mesh_runs_a_node(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    monkeypatch.setenv("ARKITEKT_MESH", value)
    assert mesh_from_env() == MeshOptions()


@pytest.mark.parametrize("value", ["0", "false", "off"])
def test_arkitekt_mesh_off(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    monkeypatch.setenv("ARKITEKT_MESH", value)
    assert mesh_from_env() is None


@pytest.mark.parametrize("value", [None, "", "auto", "AUTO"])
def test_unset_uses_the_mesh_when_it_is_available(
    monkeypatch: pytest.MonkeyPatch, value: str | None
) -> None:
    if value is not None:
        monkeypatch.setenv("ARKITEKT_MESH", value)
    assert mesh_from_env() == MeshOptions(auto=True)


def test_a_typo_is_refused_rather_than_leaving_the_mesh_off(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ARKITEKT_MESH", "sidecar")
    with pytest.raises(ValueError, match="ARKITEKT_MESH='sidecar'"):
        mesh_from_env()


def test_a_proxy_wins_over_a_node(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ARKITEKT_MESH", "1")
    monkeypatch.setenv("ARKITEKT_MESH_PROXY", PROXY)
    assert mesh_from_env() == MeshProxy(url=PROXY)


def test_the_device_code_run_asks_for_a_key_only_for_its_own_node(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ARKITEKT_MESH", "1")
    fakts = build_fakts(MANIFEST, ConnectionOptions(url=URL, no_cache=True))
    assert fakts.mesh == MeshOptions()
    assert asks_for_mesh_key(fakts) is True

    proxy = MeshProxy(url=PROXY)
    fakts = build_fakts(MANIFEST, ConnectionOptions(url=URL, no_cache=True, mesh=proxy))
    assert fakts.mesh == proxy, "what is passed wins over the environment"
    assert asks_for_mesh_key(fakts) is False


@pytest.mark.parametrize(
    "options",
    [
        ConnectionOptions(url=URL, no_cache=True, token="client:refresh"),
        ConnectionOptions(url=URL, no_cache=True, redeem_token="redeem-me"),
    ],
    ids=["token", "redeem"],
)
def test_every_grant_carries_the_mesh(
    monkeypatch: pytest.MonkeyPatch, options: ConnectionOptions
) -> None:
    monkeypatch.setenv("ARKITEKT_MESH_PROXY", PROXY)
    assert build_fakts(MANIFEST, options).mesh == MeshProxy(url=PROXY)


def test_by_default_the_mesh_is_used_when_it_is_available(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Whether a key comes is the server's call: the user can opt out of the
    mesh, and an organization without one grants none."""
    monkeypatch.setattr("fakts.mesh.bindings_installed", lambda: True)
    fakts = build_fakts(MANIFEST, ConnectionOptions(url=URL, no_cache=True))
    assert fakts.mesh == MeshOptions(auto=True)
    assert asks_for_mesh_key(fakts) is True

    # Without the bindings, no node could use a key: do not ask for one.
    monkeypatch.setattr("fakts.mesh.bindings_installed", lambda: False)
    fakts = build_fakts(MANIFEST, ConnectionOptions(url=URL, no_cache=True))
    assert asks_for_mesh_key(fakts) is False


@pytest.mark.parametrize(("passed", "expected"), [(True, MeshOptions()), (False, None)])
def test_a_bool_turns_it_on_or_off_whatever_the_environment_says(
    monkeypatch: pytest.MonkeyPatch, passed: bool, expected: MeshOptions | None
) -> None:
    monkeypatch.setenv("ARKITEKT_MESH", "0" if passed else "1")
    fakts = build_fakts(MANIFEST, ConnectionOptions(url=URL, no_cache=True, mesh=passed))
    assert fakts.mesh == expected
