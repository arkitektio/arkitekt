"""The App's catalog facade. The rules themselves are rekuest's and are tested there."""

import pytest

from arkitekt import App
from rekuest.catalogs import ComponentSpec, OperationSpec, PropSpec

SLIDER = ComponentSpec(
    name="Slider",
    accepts_children=False,
    props=(PropSpec(key="min", kind="FLOAT", required=True),),
)
BOX = ComponentSpec(name="Box", accepts_children=True)


def test_ui_catalog_reaches_the_registry() -> None:
    app = App("demo")
    app.ui_catalog("electron", components=[SLIDER, BOX], description="the desktop app")

    declared = app.registry.declared_catalogs["electron"]
    assert declared.components == (SLIDER, BOX)
    assert declared.description == "the desktop app"


def test_blok_passes_its_catalog_through() -> None:
    app = App("demo")
    app.ui_catalog("electron", components=[SLIDER, BOX])
    app.blok("panel", '<Box><Slider min="1" /></Box>', catalog="electron")

    assert app.registry.registered_bloks["panel"].catalog == "electron"


def test_a_blok_is_validated_against_the_declared_catalog() -> None:
    app = App("demo")
    app.ui_catalog("electron", components=[SLIDER, BOX])
    with pytest.raises(ValueError, match="is not registered in catalog"):
        app.blok("bad", "<Box><Slidr /></Box>", catalog="electron")


def test_declaring_a_catalog_offers_nothing() -> None:
    """A UI app registering its catalog should not be made to serve."""
    app = App("demo")
    app.ui_catalog("electron", components=[SLIDER])
    assert "rekuest" not in app.registry.services


def test_a_catalog_may_not_shadow_a_base_operation() -> None:
    app = App("demo")
    with pytest.raises(ValueError, match="cannot redefine base operations"):
        app.ui_catalog(
            "rogue", operations=[OperationSpec(name="gt", returns="BOOL", arguments=())]
        )
