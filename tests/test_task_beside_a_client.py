"""An action may take a client and the running task together.

Asking whether ``Task`` is a client used to raise (it is a protocol with data
members), so an app using a client could not offer any action that also took
``task: Task``.
"""

from arkitekt import App, Task

from .fakes import PictureClient


def test_an_action_takes_a_client_and_the_task() -> None:
    app = App("task-beside-client")

    @app.action
    def show(size: int, pictures: PictureClient, task: Task) -> str:
        """Shows."""
        return pictures.name

    definition = app.registry.implementations["show"].definition
    assert [arg.key for arg in definition.args] == ["size"]
