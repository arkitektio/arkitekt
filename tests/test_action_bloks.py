"""An action's own bloks through the App: passed to arkitekt-spec only when given, checked at decoration.

The rules are arkitekt-spec's (``tests/declare/test_action_bloks.py`` there); this pins that
``@app.workflow(bloks=[...])`` and ``@app.action(bloks=[...])`` reach the definition, that a blok
is checked against the function's dependency parameters right away, and that an action without
bloks sends what it always did.
"""

import warnings
from typing import Protocol

import pytest
from arkitekt_spec.declare.catalogs import CatalogWarning

from arkitekt import ActionBlok, App, bsx


class Arm(Protocol):
    """An arm another app runs."""

    def pick(self, slot: int) -> None:
        """Pick."""
        ...


def test_a_workflows_bloks_reach_its_definition() -> None:
    app = App("flow")
    app.registry.declare(app="arm")(Arm)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", CatalogWarning)

        @app.workflow(
            bloks=[
                ActionBlok(bsx('<Overlay><At dependency="robot"><TaskAsk /></At></Overlay>'), context="overlay", local_state={"show_path": True}, persist=["show_path"]),
                ActionBlok('<Card><Progress value="@task.progress" /></Card>', context="html"),
            ]
        )
        def move(robot: Arm, slot: int) -> None:
            """Move a slide."""
            robot.pick(slot)

    (implementation,) = [i for i in app.registry.implementations.values() if i.definition.key == "move"]
    overlay, panel = implementation.definition.bloks
    assert (overlay.context, overlay.components[0].component if overlay.components else None) == ("OVERLAY", "Overlay")
    assert [local.key for local in overlay.persist] == ["show_path"]
    assert (panel.context, panel.source) == ("HTML", '<Card><Progress value="@task.progress" /></Card>')


def test_a_blok_naming_no_parameter_is_refused_at_decoration() -> None:
    app = App("flow")
    app.registry.declare(app="arm")(Arm)

    with pytest.raises(ValueError, match="names 'stage', which is not a dependency of the action"):

        @app.workflow(bloks=[ActionBlok('<Overlay><At dependency="stage" /></Overlay>', context="overlay")])
        def move(robot: Arm, slot: int) -> None:
            """Move a slide."""
            robot.pick(slot)


def test_an_action_without_bloks_sends_none() -> None:
    app = App("flow")

    @app.action
    def double(x: int) -> int:
        """Double."""
        return 2 * x

    (implementation,) = app.registry.implementations.values()
    assert "bloks" not in implementation.definition.model_dump(mode="json")
