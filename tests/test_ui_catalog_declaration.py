"""The App's catalog and blok facade. The rules themselves are arkitekt-spec's and are tested there."""

import sys
import warnings
from collections.abc import Iterator

import pytest
from arkitekt_spec.blok.catalogs import checking_catalogs
from arkitekt_spec.declare.blok.registry import resolved_locals
from arkitekt_spec.declare.catalogs import (
    CatalogWarning,
    ComponentSpec,
    OperationSpec,
    PropSpec,
)
from arkitekt_spec.declare.catalogs.ports import scalar

from arkitekt import App, AppDeclarationError, BlokError, PortKind


def refusal(app: App[None]) -> pytest.ExceptionInfo[AppDeclarationError]:
    """What assembling ``app`` raises."""
    with pytest.raises(AppDeclarationError) as refused:
        app.declaration()
    return refused


@pytest.fixture(autouse=True)
def _catalogs_checked() -> Iterator[None]:
    """These tests declare bloks as ``arkitekt check`` loads an app: held to their catalog too.
    An app that merely registers is held to the blok language alone."""
    with checking_catalogs():
        yield


# A renderer's own components. Their names are not the base catalog's: a declared catalog
# adds to the base, which keeps its own.
SLIDER = ComponentSpec(
    name="DeskSlider",
    accepts_children=False,
    props=(PropSpec(key="min", port=scalar("FLOAT"), required=True),),
)
BOX = ComponentSpec(name="Box", accepts_children=True)
ELECTRON = '<Blok kind="agent" context="panel" catalog="electron">'


def test_ui_catalog_reaches_the_registry() -> None:
    app = App("demo")
    app.ui_catalog("electron", components=[SLIDER, BOX], description="the desktop app")

    declared = app.registry.declared_catalogs["electron"]
    assert declared.components == (SLIDER, BOX)
    assert declared.description == "the desktop app"


def test_blok_passes_its_catalog_through() -> None:
    app = App("demo")
    app.ui_catalog("electron", components=[SLIDER, BOX])
    app.blok("panel", ELECTRON + "<Box><DeskSlider min={1} /></Box></Blok>")

    assert app.registry.registered_bloks["panel"].catalog == "electron"


def test_a_blok_is_validated_against_the_declared_module() -> None:
    app = App("demo")
    app.ui_catalog("electron", components=[SLIDER, BOX])
    app.blok("bad", ELECTRON + "<Box><Slidr /></Box></Blok>", mode="strict")
    refused = refusal(app)
    assert refused.group_contains(BlokError, match="Slidr")
    (error,) = refused.value.exceptions
    assert isinstance(error, BlokError) and error.code == "catalog.unknown_component"


def test_a_catalog_finding_is_a_warning_by_default() -> None:
    app = App("demo")
    app.ui_catalog("electron", components=[SLIDER, BOX])
    app.blok("loose", ELECTRON + "<Box><Slidr /></Box></Blok>")
    with pytest.warns(CatalogWarning, match=r"\[catalog.unknown_component\]"):
        app.declaration()


def test_a_warning_is_told_once_at_the_apps_own_line() -> None:
    """Not inside ``App.blok``, and not again when the agent's input is built."""
    app = App("demo")
    app.ui_catalog("electron", components=[SLIDER, BOX])
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        line = sys._getframe().f_lineno + 1
        app.blok("loose", ELECTRON + "<Box><Slidr /></Box></Blok>")
        app.registry.get_declared_bloks()
    found = [
        warning for warning in caught if issubclass(warning.category, CatalogWarning)
    ]
    assert [
        "[catalog.unknown_component]" in str(warning.message) for warning in found
    ] == [True]
    assert (found[0].filename, found[0].lineno) == (__file__, line)


def test_declaring_a_module_offers_nothing() -> None:
    """A UI app registering its module should not be made to serve."""
    app = App("demo")
    app.ui_catalog("electron", components=[SLIDER])
    assert "rekuest" not in app.registry.clients


def test_a_module_may_not_shadow_a_base_operation() -> None:
    app = App("demo")
    app.ui_catalog(
        "rogue",
        operations=[OperationSpec(name="gt", returns=scalar("BOOL"), arguments=())],
    )
    assert refusal(app).group_contains(
        ValueError, match="cannot redefine base operations"
    )


def test_blok_declares_its_locals_and_its_queries() -> None:
    app = App("demo")
    app.blok(
        "form",
        """
        <Blok kind="agent" context="panel">
          <local name="iterations" default={15} persist />
          <query name="images" service="mikro" document="query { images { id } }" />
          <Card>
            <Slider bind={iterations} min={1} max={40} />
            <Text>{queries.images.value}</Text>
          </Card>
        </Blok>
        """,
        demo={"queries": {"images": []}},
    )

    with warnings.catch_warnings():
        # The app knows no schema for mikro, so the query is not checked: a warning.
        warnings.simplefilter("ignore", CatalogWarning)
        declared = app.registry.get_declared_bloks()["form"]
    (local,) = resolved_locals(declared, app.registry).values()
    assert (local.key, local.default, local.kind, local.persist) == (
        "iterations",
        15,
        PortKind.INT,
        True,
    )
    assert declared.demo is not None and declared.demo.queries == {"images": []}
    assert declared.vocab == 2


def test_a_blok_reading_an_undeclared_local_is_refused() -> None:
    app = App("demo")
    app.blok(
        "form",
        '<Blok kind="agent" context="panel"><Slider bind={iterations} /></Blok>',
    )
    assert refusal(app).group_contains(BlokError)


def test_a_blok_reads_then_and_draws_relative_time_with_the_time_component() -> None:
    """Nothing ticks in an expression: ``now`` and ``time.since`` are gone, ``then`` is the
    viewed moment and ``<Time relative>`` ticks by itself."""
    now = App("demo")
    now.blok("clock", '<Blok kind="agent" context="panel"><Text>{now}</Text></Blok>')
    assert refusal(now).group_contains(BlokError, match=r"roots\.unknown")

    since = App("demo")
    since.blok(
        "since",
        '<Blok kind="agent" context="panel"><Text>{time.since(t: self.run.started)}</Text></Blok>',
    )
    with pytest.warns(CatalogWarning, match=r"\[expr\.unknown_function\]"):
        since.declaration()

    then = App("demo")
    then.blok(
        "clock",
        '<Blok kind="agent" context="panel"><Card><Time value={self.run.started} relative /><Text>{then}</Text></Card></Blok>',
    )
    then.declaration()


def test_an_action_and_a_workflow_are_drawn_by_the_action_logo_they_name() -> None:
    app = App("demo")
    app.blok(
        "app",
        '<Blok kind="agent" context="logo"><Logo><Path d="M0 0" fill="brand" /></Logo></Blok>',
        default=True,
    )
    app.blok(
        "crop",
        '<Blok kind="action" context="logo"><Logo><Path d="M0 0" fill={task.running ? "brand" : "muted"} /></Logo></Blok>',
    )

    @app.action(logo="crop")
    def crop(amount: float) -> float:
        """Crop."""
        return amount

    @app.workflow(logo="crop")
    def crops(amount: float) -> float:
        """Crop twice."""
        return amount

    agent = app.registry.to_implement_agent_input()

    assert {i.interface: i.logo for i in agent.implementations or ()} == {
        "crop": "crop",
        "crops": "crop",
    }


def test_an_action_naming_a_logo_the_app_does_not_declare_is_refused() -> None:
    app = App("demo")

    @app.action(logo="nowhere")
    def crop(amount: float) -> float:
        """Crop."""
        return amount

    registry = app.registry
    with pytest.raises(
        ValueError,
        match="'nowhere', which is not an action logo blok this app declares",
    ):
        registry.to_implement_agent_input()


def test_an_action_logo_paints_with_the_palette() -> None:
    app = App("demo")
    app.blok(
        "loud",
        '<Blok kind="action" context="logo"><Logo><Path d="M0 0" fill="#fbbf24" /></Logo></Blok>',
    )
    assert refusal(app).group_contains(BlokError, match="#fbbf24")


def test_blok_passes_its_args_through() -> None:
    """A blok opened for an item: its args are ports, read as ``args.<key>``."""

    class Image:
        def __init__(self, id: str) -> None:
            self.id = id

    async def expand_image(id: str) -> Image:
        return Image(id)

    app = App("demo")
    app.register_structure(Image, "@t/image", expand=expand_image)
    app.blok(
        "inspector",
        '<Blok kind="agent" context="panel"><Text>{args.image.id}</Text></Blok>',
        args={"image": Image},
    )

    declared = app.registry.registered_bloks["inspector"]
    assert [port.identifier for port in declared.args] == ["@t/image"]

    other = App("demo")
    other.register_structure(Image, "@t/image", expand=expand_image)
    other.blok(
        "other",
        '<Blok kind="agent" context="panel"><Text>{args.dataset}</Text></Blok>',
        args={"image": Image},
    )
    assert refusal(other).group_contains(BlokError)


def test_a_catalog_never_redefines_a_component_of_the_base() -> None:
    """A catalog only adds: its own ``Slider`` beside the base catalog's is refused."""
    app = App("demo")
    own_slider = ComponentSpec(
        name="Slider",
        accepts_children=False,
        props=(PropSpec(key="min", port=scalar("FLOAT"), required=True),),
    )
    app.ui_catalog("electron", components=[own_slider, BOX])
    assert refusal(app).group_contains(ValueError, match="redefines <Slider> of base@4")


def test_a_blok_naming_a_catalog_not_known_here_is_warned() -> None:
    app = App("demo")
    app.blok(
        "panel",
        '<Blok kind="agent" context="panel" catalog="nowhere"><Thing /></Blok>',
    )
    with pytest.warns(CatalogWarning, match=r"\[catalog.unknown\]"):
        app.declaration()


def test_an_app_that_merely_registers_is_held_to_the_language_alone() -> None:
    """What a catalog says is checked by whoever draws the blok, and by ``arkitekt check``."""
    with checking_catalogs(False), warnings.catch_warnings():
        warnings.simplefilter("error", CatalogWarning)
        loose = App("demo")
        loose.blok(
            "loose",
            '<Blok kind="agent" context="panel"><Slidr /></Blok>',
            mode="strict",
        )
        loose.declaration()

        wrong = App("demo")
        wrong.blok(
            "wrong",
            '<Blok kind="agent" context="panel"><Text>{nothing.here}</Text></Blok>',
        )
        assert refusal(wrong).group_contains(BlokError, match="roots.unknown")
