"""An action's own bloks through the App: passed to arkitekt-spec only when given, checked at assembly.

The rules are arkitekt-spec's (``tests/declare/test_action_bloks.py`` there); this pins that
``@app.workflow(bloks=[...])`` and ``@app.action(bloks=[...])`` reach the definition, that a blok
is checked against the function's dependency parameters when the app is assembled, and that an
action without bloks sends what it always did.
"""

import warnings
from typing import Protocol

import pytest
from arkitekt_spec.declare.blok.registry import resolved_locals
from arkitekt_spec.declare.catalogs import CatalogWarning

from arkitekt import ActionBlok, App, AppDeclarationError


class Arm(Protocol):
    """An arm another app runs."""

    def pick(self, slot: int) -> None:
        """Pick."""
        ...


SPACE = '<Blok kind="action" context="scene"><Space room="lab"><Placed dep="robot"><ask /></Placed></Space></Blok>'


def test_a_workflows_bloks_reach_its_definition() -> None:
    app = App("flow")
    app.declare(app="arm")(Arm)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", CatalogWarning)

        @app.workflow(
            bloks=[
                SPACE,
                ActionBlok(
                    '<Blok kind="action" context="panel"><local name="verbose" default={false} persist />'
                    "<Card><Progress value={task.progress} /><Switch bind={verbose} /></Card></Blok>",
                    description="The run's progress",
                ),
            ]
        )
        def move(robot: Arm, slot: int) -> None:
            """Move a slide."""
            robot.pick(slot)

        (implementation,) = [
            i
            for i in app.registry.implementations.values()
            if i.definition.key == "move"
        ]
    space, panel = implementation.definition.bloks
    assert (space.context, space.source) == ("SCENE", SPACE)
    assert (panel.context, panel.phase, panel.vocab) == ("PANEL", "RUN", 2)


def test_a_blok_naming_no_parameter_is_refused_at_assembly() -> None:
    app = App("flow")
    app.declare(app="arm")(Arm)

    @app.workflow(
        bloks='<Blok kind="action" context="scene"><Space room="lab"><Placed dep="stage" /></Space></Blok>'
    )
    def move(robot: Arm, slot: int) -> None:
        """Move a slide."""
        robot.pick(slot)

    with pytest.raises(AppDeclarationError) as refused:
        app.declaration()
    assert refused.group_contains(
        ValueError, match=r"'stage' is not a dependency of the blok .*\[deps.unknown\]"
    )


def test_an_action_without_bloks_sends_none() -> None:
    app = App("flow")

    @app.action
    def double(x: int) -> int:
        """Double."""
        return 2 * x

    (implementation,) = app.registry.implementations.values()
    assert "bloks" not in implementation.definition.model_dump(mode="json")


def test_a_local_without_kind_takes_it_from_its_use() -> None:
    """``<local name="factor" />`` is enough: the argument it is passed to whole types it."""
    app = App("flow")

    @app.action
    def scale(factor: float) -> float:
        """Scale."""
        return factor

    app.blok(
        "panel",
        '<Blok kind="agent" context="panel"><local name="factor" /><local name="note" />'
        "<Card><Button onClick={self.scale(factor: factor) into run}>Go</Button><Input bind={note} /></Card></Blok>",
    )

    built = {
        local.key: local
        for local in resolved_locals(
            app.registry.get_declared_bloks()["panel"], app.registry
        ).values()
    }
    assert (built["factor"].kind, built["note"].kind) == ("FLOAT", "STRING")


def test_a_local_like_an_argument_borrows_its_port() -> None:
    app = App("flow")

    @app.action
    def move(slot: int = 3) -> int:
        """Move.

        Args:
            slot: Where to.
        """
        return slot

    app.blok(
        "panel",
        '<Blok kind="agent" context="panel"><local name="slot" like="self.move.slot" persist />'
        "<Card><Slider bind={slot} min={0} max={9} /><Button onClick={self.move(slot: slot)}>Go</Button></Card></Blok>",
    )

    (local,) = resolved_locals(
        app.registry.get_declared_bloks()["panel"], app.registry
    ).values()
    assert (local.kind, local.default, local.persist, local.description) == (
        "INT",
        3,
        True,
        "Where to.",
    )


def test_a_local_like_an_unknown_argument_is_refused() -> None:
    app = App("flow")

    @app.action
    def move(slot: int) -> int:
        """Move."""
        return slot

    app.blok(
        "panel",
        '<Blok kind="agent" context="panel"><local name="x" like="self.move.nope" /><Card><Slider bind={x} /></Card></Blok>',
    )
    with pytest.raises(AppDeclarationError) as refused:
        app.declaration()
    assert refused.group_contains(ValueError, match="local.like")


def test_an_untold_local_is_any_and_no_error() -> None:
    app = App("flow")
    with warnings.catch_warnings():
        warnings.simplefilter("error", CatalogWarning)
        app.blok(
            "panel",
            '<Blok kind="agent" context="panel"><local name="x" /><Card><Text>{x}</Text></Card></Blok>',
        )
        (local,) = resolved_locals(
            app.registry.get_declared_bloks()["panel"], app.registry
        ).values()
    assert local.kind == "ANY"


def test_an_action_declares_a_blok_for_starting_a_run() -> None:
    app = App("flow")
    app.declare(app="arm")(Arm)

    @app.workflow(
        bloks='<Blok kind="assign" context="panel"><Card><args /><Button onClick={assign.start()}>Start</Button></Card></Blok>'
    )
    def move(robot: Arm, slot: int) -> None:
        """Move a slide."""
        robot.pick(slot)

    (implementation,) = [
        i for i in app.registry.implementations.values() if i.definition.key == "move"
    ]
    (blok,) = implementation.definition.bloks
    assert (blok.phase, blok.context) == ("ASSIGN", "PANEL")
