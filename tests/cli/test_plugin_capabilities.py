"""A flavour's capabilities travel with every record made of it.

What a flavour must be granted where it runs (``capabilities`` in its ``config.yaml``) is read
by whoever installs it — konstruktor, a deployer — from the deployments file or the release.
Nothing here needs docker: the records are written straight from the flavour.
"""

import pytest
import typer
import yaml
from arkitekt_spec import AppManifest, ContainerEngineCapability, FolderCapability, Inspection
from typer.testing import CliRunner

from arkitekt.cli.commands.plugin.io import generate_build, generate_deployment, get_flavours
from arkitekt.cli.main import cli_app


def _init(tmp_path):
    return CliRunner().invoke(
        cli_app,
        ["--work-dir", str(tmp_path), "plugin", "init", "--arkitekt-version", "0.0.1"],
        input="n\n",
    )


def _declare(tmp_path, capabilities):
    config = tmp_path / ".arkitekt" / "flavours" / "vanilla" / "config.yaml"
    written = yaml.safe_load(config.read_text())
    written["capabilities"] = capabilities
    config.write_text(yaml.dump(written))


def test_a_new_flavour_needs_nothing_granted(tmp_path):
    _init(tmp_path)
    assert get_flavours(base_dir=str(tmp_path))["vanilla"].capabilities == []


def test_capabilities_reach_the_build_and_the_deployments_file(tmp_path):
    _init(tmp_path)
    _declare(
        tmp_path,
        [
            {"kind": "container_engine", "name": "engine"},
            {"kind": "folder", "name": "data", "target": "/data"},
        ],
    )
    flavour = get_flavours(base_dir=str(tmp_path))["vanilla"]
    granted = [ContainerEngineCapability(name="engine"), FolderCapability(name="data", target="/data")]
    assert flavour.capabilities == granted

    build = generate_build(
        "run",
        "build-id",
        "vanilla",
        flavour,
        AppManifest(identifier="engine", version="0.1.0"),
        Inspection(),
        base_dir=str(tmp_path),
    )
    assert build.capabilities == granted

    deployed = generate_deployment("run", build, "org/engine:0.1.0", base_dir=str(tmp_path))
    assert deployed.capabilities == granted
    written = yaml.safe_load((tmp_path / ".arkitekt" / "deployments.yaml").read_text())
    assert written["app_images"][0]["capabilities"][0] == {
        "kind": "container_engine",
        "name": "engine",
        "required": True,
        "target": "/var/run/docker.sock",
    }


def test_a_typo_in_a_capability_is_refused_when_the_flavour_is_read(tmp_path, capsys):
    _init(tmp_path)
    _declare(tmp_path, [{"kind": "folder", "name": "data", "target": "/data", "writable": True}])
    with pytest.raises(typer.Exit):
        get_flavours(base_dir=str(tmp_path))
    assert "capabilities.0.folder.writable" in capsys.readouterr().err
