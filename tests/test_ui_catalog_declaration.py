"""The App's module and blok facade. The rules themselves are arkitekt-spec's and are tested there."""

import sys
import warnings

import pytest
from arkitekt_spec.declare.catalogs import CatalogWarning, ComponentSpec, OperationSpec, PropSpec

from arkitekt import App, BlokError, Local, PortKind, Query

# A renderer's own components. Their names are not the standard catalogs': a declared module
# is drawn beside base and the standard catalogs, which keep theirs.
SLIDER = ComponentSpec(
    name="DeskSlider",
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


def test_blok_passes_its_module_through() -> None:
    app = App("demo")
    app.ui_catalog("electron", components=[SLIDER, BOX])
    app.blok("panel", "<Html><Box><DeskSlider min={1} /></Box></Html>", module="electron")

    assert app.registry.registered_bloks["panel"].module == "electron"


def test_a_blok_is_validated_against_the_declared_module() -> None:
    app = App("demo")
    app.ui_catalog("electron", components=[SLIDER, BOX])
    with pytest.raises(BlokError, match="Slidr") as refused:
        app.blok("bad", "<Html><Box><Slidr /></Box></Html>", module="electron", mode="strict")
    assert refused.value.code == "catalog.unknown_component"


def test_a_catalog_finding_is_a_warning_by_default() -> None:
    app = App("demo")
    app.ui_catalog("electron", components=[SLIDER, BOX])
    with pytest.warns(CatalogWarning, match=r"\[catalog.unknown_component\]"):
        app.blok("loose", "<Html><Box><Slidr /></Box></Html>", module="electron")


def test_a_warning_is_told_once_at_the_apps_own_line() -> None:
    """Not inside ``App.blok``, and not again when the agent's input is built."""
    app = App("demo")
    app.ui_catalog("electron", components=[SLIDER, BOX])
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        line = sys._getframe().f_lineno + 1
        app.blok("loose", "<Html><Box><Slidr /></Box></Html>", module="electron")
        app.registry.get_declared_bloks()
    found = [warning for warning in caught if issubclass(warning.category, CatalogWarning)]
    assert ["[catalog.unknown_component]" in str(warning.message) for warning in found] == [True]
    assert (found[0].filename, found[0].lineno) == (__file__, line)


def test_declaring_a_module_offers_nothing() -> None:
    """A UI app registering its module should not be made to serve."""
    app = App("demo")
    app.ui_catalog("electron", components=[SLIDER])
    assert "rekuest" not in app.registry.services


def test_a_module_may_not_shadow_a_base_operation() -> None:
    app = App("demo")
    with pytest.raises(ValueError, match="cannot redefine base operations"):
        app.ui_catalog(
            "rogue", operations=[OperationSpec(name="gt", returns="BOOL", arguments=())]
        )


def test_blok_declares_its_locals_and_its_queries() -> None:
    app = App("demo")
    app.blok(
        "form",
        """
        <Html>
          <Card>
            <Slider bind={iterations} min={1} max={40} />
            <Text>{queries.images.value}</Text>
          </Card>
        </Html>
        """,
        locals={"iterations": Local(15, persist=True)},
        queries={"images": Query(service="mikro", document="query { images { id } }")},
        demo={"queries": {"images": []}},
    )

    with warnings.catch_warnings():
        # The app knows no schema for mikro, so the query is not checked: a warning.
        warnings.simplefilter("ignore", CatalogWarning)
        declared = app.registry.get_declared_bloks()["form"]
    (local,) = declared.locals
    assert (local.key, local.default, local.kind, local.persist) == ("iterations", 15, PortKind.INT, True)
    assert [query.key for query in declared.queries] == ["images"]
    assert declared.demo is not None and declared.demo.queries == {"images": []}
    assert declared.vocab == 2


def test_a_blok_reading_an_undeclared_local_is_refused() -> None:
    app = App("demo")
    with pytest.raises(BlokError):
        app.blok("form", "<Html><Slider bind={iterations} /></Html>")


def test_a_blok_reads_then_and_draws_relative_time_with_the_time_component() -> None:
    """Nothing ticks in an expression: ``now`` and ``time.since`` are gone, ``then`` is the
    viewed moment and ``<Time relative>`` ticks by itself."""
    app = App("demo")
    with pytest.raises(BlokError, match=r"roots\.unknown"):
        app.blok("clock", "<Html><Text>{now}</Text></Html>")
    with pytest.warns(CatalogWarning, match=r"\[expr\.unknown_function\]"):
        app.blok("since", "<Html><Text>{time.since(t: self.run.started)}</Text></Html>")
    app.blok("clock", "<Html><Card><Time value={self.run.started} relative /><Text>{then}</Text></Card></Html>")


def test_an_action_and_a_workflow_are_drawn_by_the_action_logo_they_name() -> None:
    app = App("demo")
    app.blok("app", '<AgentLogo><Path d="M0 0" fill="brand" /></AgentLogo>', default=True)
    app.blok("crop", '<ActionLogo><Path d="M0 0" fill={task.running ? "brand" : "muted"} /></ActionLogo>')

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
    with pytest.raises(BlokError, match="#fbbf24"):
        app.blok("loud", '<ActionLogo><Path d="M0 0" fill="#fbbf24" /></ActionLogo>')


def test_blok_passes_its_args_through() -> None:
    """A blok opened for an item: its args are ports, read as ``args.<key>``."""

    class Image:
        def __init__(self, id: str) -> None:
            self.id = id

    app = App("demo")

    @app.registry.structure_registry.structure("@t/image")
    async def expand_image(id: str) -> Image:
        return Image(id)

    app.blok("inspector", "<Html><Text>{args.image.id}</Text></Html>", args={"image": Image})

    declared = app.registry.registered_bloks["inspector"]
    assert [port.identifier for port in declared.args] == ["@t/image"]
    with pytest.raises(BlokError):
        app.blok("other", "<Html><Text>{args.dataset}</Text></Html>", args={"image": Image})


def test_a_module_may_shadow_a_standard_component() -> None:
    """The module's ``Slider`` is drawn, with a ``catalog.shadow`` warning where it is used."""
    app = App("demo")
    own_slider = ComponentSpec(name="Slider", accepts_children=False, props=(PropSpec(key="min", kind="FLOAT", required=True),))
    app.ui_catalog("electron", components=[own_slider, BOX])
    with pytest.warns(CatalogWarning, match=r"\[catalog.shadow\]"):
        app.blok("panel", "<Html><Box><Slider min={1} /></Box></Html>", module="electron")


def test_a_blok_naming_an_undeclared_module_is_warned() -> None:
    app = App("demo")
    with pytest.warns(CatalogWarning, match=r"\[module.unknown\]"):
        app.blok("panel", "<Html><Thing /></Html>", module="nowhere")
