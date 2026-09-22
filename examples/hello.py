# /// script
# requires-python = ">=3.11"
# dependencies = ["arkitekt>=3"]
# ///
"""Offering: the smallest possible app — one action, offered until you stop it.

Run:  uv run --script examples/hello.py

The script connects to the Arkitekt server in ``$FAKTS_URL`` (or the public
deployment), authenticates once in your browser, and then `greet` is callable
from the UI, from a workflow, or from any other app.
"""

from typing import Annotated

from arkitekt import App, Description, run

app = App("hello", "0.1.0")


@app.action
def greet(
    name: Annotated[str, Description("Who to greet")] = "world",
    times: Annotated[int, Description("How often to say it")] = 1,
) -> str:
    """Greet

    Says hello. The docstring's first line is the action's title, the rest its
    description — this is the whole UI, generated from the signature.
    """
    return " ".join([f"Hello {name}!"] * times)


if __name__ == "__main__":
    # Nothing above this line connects: an App is a declaration. `run` is what
    # authenticates, registers the action and blocks.
    run(app)
