"""An action's own bloks through the App: passed to arkitekt-spec only when given, checked at decoration.

The rules are arkitekt-spec's (``tests/declare/test_action_bloks.py`` there); this pins that
``@app.workflow(bloks=[...])`` and ``@app.action(bloks=[...])`` reach the definition, that a blok
is checked against the function's dependency parameters right away, and that an action without
bloks sends what it always did.
"""

import json
import warnings
from typing import Protocol

import pytest
from arkitekt_spec.declare.catalogs import CatalogWarning

from arkitekt_runtime import messages
from arkitekt_spec.blok.bsx import parse_bsx
from arkitekt_spec.blok.catalogs import default_view
from arkitekt_spec.declare.blok.infer import resolve_scope
from arkitekt_spec.declare.blok.registry import resolved_locals
from arkitekt_spec.declare.blok.validate import BlokScope

from arkitekt import ActionBlok, App, Local


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
                '<Overlay><Anchor dep="robot"><ask /></Anchor></Overlay>',
                ActionBlok(
                    "<Html><Card><Progress value={task.progress} /><Switch bind={verbose} /></Card></Html>",
                    locals={"verbose": Local(False, persist=True)},
                ),
            ]
        )
        def move(robot: Arm, slot: int) -> None:
            """Move a slide."""
            robot.pick(slot)

    (implementation,) = [i for i in app.registry.implementations.values() if i.definition.key == "move"]
    overlay, panel = implementation.definition.bloks
    assert (overlay.context, overlay.source) == ("OVERLAY", '<Overlay><Anchor dep="robot"><ask /></Anchor></Overlay>')
    assert (panel.context, panel.vocab) == ("HTML", 2)
    assert [(local.key, local.persist) for local in panel.locals] == [("verbose", True)]


def test_a_blok_naming_no_parameter_is_refused_at_decoration() -> None:
    app = App("flow")
    app.registry.declare(app="arm")(Arm)

    with pytest.raises(ValueError, match="names 'stage', which is not a dependency of the action"):

        @app.workflow(bloks='<Overlay><Anchor dep="stage" /></Overlay>')
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


def test_a_local_without_kind_takes_it_from_its_use() -> None:
    """``Local()`` is enough: the argument it is passed to whole types it."""
    app = App("flow")

    @app.action
    def scale(factor: float) -> float:
        """Scale."""
        return factor

    app.blok(
        "panel",
        "<Html><Card><Button onClick={self.scale(factor: factor) into run}>Go</Button><Input bind={note} /></Card></Html>",
        locals={"factor": Local(), "note": Local()},
    )

    blok = app.registry.get_declared_bloks()["panel"]
    # Sent as written (the server infers the same); resolved, they are typed by their use.
    assert all("kind" not in local.model_fields_set for local in blok.locals or ())
    built = {local.key: local for local in resolved_locals(blok, app.registry)}
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
        "<Html><Card><Slider bind={slot} min={0} max={9} /><Button onClick={self.move(slot: slot)}>Go</Button></Card></Html>",
        locals={"slot": Local.like(move.interface, "slot", persist=True)},
    )

    (local,) = app.registry.get_declared_bloks()["panel"].locals
    assert (local.kind, local.default, local.persist, local.description) == ("INT", 3, True, "Where to.")


def test_a_local_like_an_unknown_argument_is_refused() -> None:
    app = App("flow")

    @app.action
    def move(slot: int) -> int:
        """Move."""
        return slot

    with pytest.raises(ValueError, match="local.like"):
        app.blok("panel", "<Html><Card><Slider bind={x} /></Card></Html>", locals={"x": Local.like(move.interface, "nope")})


def test_an_untold_local_is_any_and_no_error() -> None:
    app = App("flow")
    with warnings.catch_warnings():
        warnings.simplefilter("error", CatalogWarning)
        app.blok("panel", "<Html><Card><Text>{x}</Text></Card></Html>", locals={"x": Local()})
    (local,) = resolved_locals(app.registry.get_declared_bloks()["panel"], app.registry)
    assert local.kind == "ANY"


def test_kind_less_locals_register_without_a_kind() -> None:
    """An agent's and an action's bloks send a left-out kind as left out: the server infers it
    (a given ANY it would keep). Resolved, the action blok's local is typed by its control."""
    app = App("flow")

    @app.action(bloks=[ActionBlok("<Html><Card><Switch bind={verbose} /></Card></Html>", locals={"verbose": Local()})])
    def scale(factor: float) -> float:
        """Scale."""
        return factor

    app.blok("panel", "<Html><Card><Button onClick={self.scale(factor: factor)}>Go</Button></Card></Html>", locals={"factor": Local()})

    agent_input = app.registry.to_implement_agent_input(name="flow")
    register = messages.Register(token="t", **agent_input.model_dump(mode="json", by_alias=False, exclude_unset=True))
    wire = json.loads(register.model_dump_json())

    [panel] = [blok for blok in wire["bloks"] if blok["key"] == "panel"]
    [action_blok] = wire["implementations"][0]["definition"]["bloks"]
    assert [local.get("kind") for local in panel["locals"]] == [None]
    assert [local.get("kind") for local in action_blok["locals"]] == [None]

    (implementation,) = app.registry.implementations.values()
    (declared,) = implementation.definition.bloks
    tree = declared.components[0] if declared.components else parse_bsx(declared.source or "", view=default_view())
    resolved = resolve_scope(tree, BlokScope(kind="action", locals=tuple(declared.locals or ())), default_view())
    assert [(local.key, local.kind) for local in resolved.locals] == [("verbose", "BOOL")]
