"""`@app.action(protocols=...)`: the hints an action declares reach its definition.

The hint itself is the spec's (arkitekt-spec ``tests/declare/test_protocol_hints.py``);
what is tested here is that every way an app registers an action passes it on.
"""

from arkitekt import App


def attach(scene: str) -> str:
    """Attach a scene."""
    return scene


def test_the_decorator_passes_them_on() -> None:
    app = App("hints")
    app.action(protocols=["on_scene_init"])(attach)
    assert app.registry.implementations["attach"].definition.protocols == ("on_scene_init",)


def test_the_register_twin_passes_them_on() -> None:
    app = App("hints")
    app.register_action(attach, protocols=["on_scene_init"])
    assert app.registry.implementations["attach"].definition.protocols == ("on_scene_init",)


def test_a_workflow_passes_them_on() -> None:
    app = App("hints")
    app.workflow(protocols=["on_scene_leave"])(attach)
    assert app.registry.implementations["attach"].definition.protocols == ("on_scene_leave",)


def test_an_action_without_hints_has_none() -> None:
    app = App("hints")
    app.action(attach)
    assert app.registry.implementations["attach"].definition.protocols == ()
