"""The App's catalog facade. The rules themselves are rekuest's and are tested there."""

import pytest
from arkitekt_spec.declare.catalogs import ComponentSpec, OperationSpec, PropSpec

from arkitekt import App

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
        app.blok("bad", "<Box><Slidr /></Box>", catalog="electron", mode="strict")


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


def test_blok_passes_its_local_state_through() -> None:
    app = App("demo")
    app.blok(
        "form",
        '<Slider bind="form.iterations" />',
        local_state={"form": {"iterations": 15}},
    )

    assert app.registry.registered_bloks["form"].local_state == {"form": {"iterations": 15}}
    assert app.registry.get_declared_bloks()["form"].demo_state == {"form": {"iterations": 15}}


def test_blok_passes_its_persisted_locals_through() -> None:
    app = App("demo")
    app.blok(
        "posed",
        '<Slider bind="pose.x" />',
        local_state={"pose": {"x": 0}},
        persist={"pose": "Where the gizmo left it"},
    )

    (local,) = app.registry.get_declared_bloks()["posed"].persist
    assert (local.key, local.description) == ("pose", "Where the gizmo left it")


SVG = ComponentSpec(name="SVG", accepts_children=True, children_context="LOGO", not_downstream_of=("SVG", "ActionLogo"))
ACTION_LOGO = ComponentSpec(name="ActionLogo", accepts_children=True, children_context="LOGO", not_downstream_of=("SVG", "ActionLogo"))
PATH = ComponentSpec(
    name="Path",
    context="LOGO",
    downstream_of=("SVG", "ActionLogo"),
    props=(PropSpec(key="d", kind="STRING", required=True), PropSpec(key="fill", kind="STRING", required=False)),
)


def test_an_action_and_a_workflow_are_drawn_by_the_action_logo_they_name() -> None:
    app = App("demo")
    app.ui_catalog("drawing", components=[SVG, ACTION_LOGO, PATH])
    app.blok("app", '<SVG><Path d="M0 0" fill="#fbbf24" /></SVG>', catalog="drawing", context="logo", default=True)
    app.blok("crop", '<ActionLogo><Path d="M0 0" fill="brand" /></ActionLogo>', catalog="drawing", context="action_logo")

    @app.action(logo="crop")
    def crop(amount: float) -> float:
        """Crop."""
        return amount

    @app.workflow(logo="crop")
    def crops(amount: float) -> float:
        """Crop twice."""
        return amount

    agent = app.registry.to_implement_agent_input()

    assert {i.interface: i.logo for i in agent.implementations or ()} == {"crop": "crop", "crops": "crop"}


def test_an_action_naming_a_logo_the_app_does_not_declare_is_refused() -> None:
    app = App("demo")

    @app.action(logo="nowhere")
    def crop(amount: float) -> float:
        """Crop."""
        return amount

    with pytest.raises(ValueError, match="'nowhere', which is not an action logo blok this app declares"):
        app.registry.to_implement_agent_input()


def test_an_action_logo_paints_with_the_palette() -> None:
    app = App("demo")
    app.ui_catalog("drawing", components=[SVG, ACTION_LOGO, PATH])
    with pytest.raises(ValueError, match="not '#fbbf24' in 'fill'"):
        app.blok("loud", '<ActionLogo><Path d="M0 0" fill="#fbbf24" /></ActionLogo>', catalog="drawing", context="action_logo")


def test_blok_passes_its_args_through() -> None:
    """A blok opened for an item: its args are ports, and ``@args`` is seeded null."""

    class Image:
        def __init__(self, id: str) -> None:
            self.id = id

    app = App("demo")

    @app.registry.structure_registry.structure("@t/image")
    async def expand_image(id: str) -> Image:
        return Image(id)

    app.blok("inspector", '<Text text="@args.image" />', args={"image": Image})

    declared = app.registry.registered_bloks["inspector"]
    assert [port.identifier for port in declared.args] == ["@t/image"]
    assert declared.local_state == {"args": {"image": None}}
