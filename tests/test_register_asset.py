"""An app names the files it brings, relative to where it is written."""

from pathlib import Path

import pytest

from arkitekt import App, AssetKind, bsx

HERE = Path(__file__).parent
GLB = b"glTF" + b"\x02\x00\x00\x00" + b"rest"


def test_an_apps_directory_is_where_it_is_constructed() -> None:
    assert App("asset-app", "0.1.0").registry.root == HERE


def test_an_app_registers_a_model_and_names_it_in_a_scene_blok(tmp_path: Path) -> None:
    (tmp_path / "models").mkdir()
    (tmp_path / "models" / "scope.glb").write_bytes(GLB)
    app = App("asset-app", "0.1.0", root=tmp_path)

    app.register_asset("scope", "models/scope.glb")
    app.blok("view", bsx('<Scene><Model src="@self.assets.scope" /></Scene>'))

    asset = app.registry.registered_assets["scope"]
    assert asset.kind is AssetKind.MODEL_3D and asset.path == tmp_path / "models" / "scope.glb"
    assets = app.registry.to_implement_agent_input(name="asset-app").assets
    assert assets is not None
    (declared,) = assets
    assert declared.name == "scope" and declared.ref.startswith("sha256:")


def test_a_file_outside_the_app_is_not_its_asset(tmp_path: Path) -> None:
    (tmp_path / "app").mkdir()
    (tmp_path / "elsewhere.glb").write_bytes(GLB)
    app = App("asset-app", "0.1.0", root=tmp_path / "app")

    with pytest.raises(ValueError, match="inside the app's directory"):
        app.register_asset("scope", "../elsewhere.glb")


def test_an_app_names_a_file_it_does_not_ship_by_its_source_and_hash(tmp_path: Path) -> None:
    app = App("asset-app", "0.1.0", root=tmp_path)
    ref = "sha256:" + "9f" * 32

    app.register_asset("robot", source="https://vendor.example/ur5.glb", ref=ref)
    app.blok("view", bsx('<Scene><Model src="@self.assets.robot" /></Scene>'))

    assets = app.registry.to_implement_agent_input(name="asset-app").assets
    assert assets is not None
    (declared,) = assets
    assert declared.model_dump(exclude_unset=True) == {"name": "robot", "kind": "MODEL_3D", "ref": ref, "source": "https://vendor.example/ur5.glb"}
    with pytest.raises(ValueError, match="give exactly one"):
        app.register_asset("other")
