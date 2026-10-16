"""Connection options as a value, none, or a cascade of sources (``arkitekt.app.sources``).

``"discover"`` (every option's default) is the command line, then the environment, then
the built-in default; ``None`` is none, and nothing is looked up.
"""

from __future__ import annotations

import pytest
from fakts.mesh import MeshOptions, MeshProxy

from arkitekt.app.fakts import (
    resolve_insecure_transport,
    resolve_mesh,
    resolve_reauth,
    resolve_token,
    resolve_url,
)
from arkitekt.app.sources import DISCOVER, SOURCES, cascade, from_argv, is_source, resolve
from arkitekt.constants import DEFAULT_ARKITEKT_URL
from arkitekt.device_id import resolve_device_id

ENVS = (
    "FAKTS_URL",
    "FAKTS_TOKEN",
    "FAKTS_MANDATE_KEY",
    "ARKITEKT_REAUTH",
    "ARKITEKT_MESH",
    "ARKITEKT_MESH_PROXY",
    "ARKITEKT_DEVICE_ID",
    "ARKITEKT_SUPERVISOR",
    "FAKTS_ALLOW_INSECURE_TRANSPORT",
)


@pytest.fixture(autouse=True)
def clean(monkeypatch: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    for name in ENVS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr("sys.argv", ["app.py"])
    return monkeypatch


def supervisor(value: object) -> object:
    return resolve(value, flag="supervisor", env="ARKITEKT_SUPERVISOR", default=lambda: "built-in", parse=str)


def test_the_eight_spellings_are_sources_and_anything_else_is_a_value() -> None:
    assert SOURCES == {"discover", "arg", "env", "default", "arg-env", "arg-default", "env-default", "arg-env-default"}
    assert cascade(DISCOVER) == cascade("arg-env-default") == ("arg", "env", "default")
    assert not is_source("plugin_engine") and not is_source(None) and not is_source(True)


def test_a_value_is_used_and_none_is_none(clean: pytest.MonkeyPatch) -> None:
    clean.setenv("ARKITEKT_SUPERVISOR", "from-env")
    clean.setattr("sys.argv", ["app.py", "--supervisor", "from-arg"])

    assert supervisor("plugin_engine") == "plugin_engine"
    assert supervisor(None) is None


def test_the_cascade_is_tried_in_order_and_the_first_hit_wins(clean: pytest.MonkeyPatch) -> None:
    assert supervisor("discover") == "built-in"
    assert supervisor("arg-env") is None  # no default in the cascade: nothing found is none

    clean.setenv("ARKITEKT_SUPERVISOR", "from-env")
    assert supervisor("discover") == "from-env"
    assert supervisor("default") == "built-in"
    assert supervisor("arg") is None

    clean.setattr("sys.argv", ["app.py", "--supervisor=from-arg"])
    assert supervisor("discover") == "from-arg"
    assert supervisor("env-default") == "from-env"


def test_the_command_line_is_read_without_being_consumed() -> None:
    assert from_argv("supervisor", ["--supervisor", "a"]) == "a"
    assert from_argv("supervisor", ["--supervisor=a", "--supervisor", "b"]) == "b"
    assert from_argv("supervisor", ["--other", "a"]) is None
    assert from_argv("supervisor", ["--supervisor", "--next"]) == ""
    # A switch never takes the argument after it.
    assert from_argv("reauth", ["--reauth", "positional"], boolean=True) == ""
    assert from_argv("reauth", ["--reauth=0"], boolean=True) == "0"


def test_an_empty_variable_is_unset(clean: pytest.MonkeyPatch) -> None:
    clean.setenv("ARKITEKT_SUPERVISOR", "  ")
    assert supervisor("env-default") == "built-in"


def test_a_typo_raises_only_when_its_source_is_consulted(clean: pytest.MonkeyPatch) -> None:
    clean.setenv("ARKITEKT_REAUTH", "yes please")
    assert resolve_reauth("default") is False
    assert resolve_reauth(True) is True
    with pytest.raises(ValueError, match="ARKITEKT_REAUTH"):
        resolve_reauth(DISCOVER)


# --- each option -------------------------------------------------------------------------------


def test_url(clean: pytest.MonkeyPatch) -> None:
    clean.setenv("FAKTS_URL", "http://lab/")
    assert resolve_url() == "http://lab"
    assert resolve_url("default") == DEFAULT_ARKITEKT_URL
    # A run cannot connect to no server: None is read as "discover".
    assert resolve_url(None) == "http://lab"
    clean.delenv("FAKTS_URL")
    with pytest.raises(ValueError, match="No fakts server"):
        resolve_url("env")


def test_token(clean: pytest.MonkeyPatch) -> None:
    clean.setenv("FAKTS_TOKEN", "cid:refresh")
    assert resolve_token() == "cid:refresh"
    assert resolve_token(None) is None
    clean.setattr("sys.argv", ["app.py", "--token", "other:refresh"])
    assert resolve_token() == "other:refresh"


def test_reauth_false_now_beats_the_environment(clean: pytest.MonkeyPatch) -> None:
    clean.setenv("ARKITEKT_REAUTH", "1")
    assert resolve_reauth() is True
    assert resolve_reauth(False) is False
    clean.delenv("ARKITEKT_REAUTH")
    clean.setattr("sys.argv", ["app.py", "--reauth"])
    assert resolve_reauth() is True


def test_mesh(clean: pytest.MonkeyPatch) -> None:
    assert resolve_mesh() == MeshOptions(auto=True)
    assert resolve_mesh(None) is None and resolve_mesh(False) is None
    assert resolve_mesh(True) == MeshOptions()
    clean.setenv("ARKITEKT_MESH", "0")
    assert resolve_mesh() is None
    assert resolve_mesh("default") == MeshOptions(auto=True)
    clean.setattr("sys.argv", ["app.py", "--mesh", "http://proxy:9000"])
    assert resolve_mesh() == MeshProxy(url="http://proxy:9000")


def test_insecure_transport(clean: pytest.MonkeyPatch) -> None:
    assert resolve_insecure_transport() is False
    clean.setenv("FAKTS_ALLOW_INSECURE_TRANSPORT", "1")
    assert resolve_insecure_transport() is True
    assert resolve_insecure_transport(False) is False
    assert resolve_insecure_transport("default") is False


def test_device_id(clean: pytest.MonkeyPatch) -> None:
    clean.setattr("arkitekt.device_id.machine_device_id", lambda: "machine")
    assert resolve_device_id() == "machine"
    assert resolve_device_id(None) is None
    clean.setenv("ARKITEKT_DEVICE_ID", "from-env")
    assert resolve_device_id() == "from-env"
    assert resolve_device_id("default") == "machine"
    clean.setattr("sys.argv", ["app.py", "--device-id", "from-arg"])
    assert resolve_device_id() == "from-arg"
