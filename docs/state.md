# State, not getters

An action that only reads something back is an antipattern:

```python
@app.action
def get_position() -> Position:      # don't
    return stage.position()
```

Whoever calls it gets a value that is already old, has to call again to see it
change, and pays a task for every look. A UI polls it, a workflow assigns it
between its real steps, and two callers never agree on what they saw.

Publish it instead. A **state** is a class whose instances the platform keeps in
front of everyone who watches: the UI shows it live, another app reads it or
reacts to it, and nobody asks.

```python
@app.state
class Stage:
    """Where the stage is, in micrometers."""
    x_um: float = 0.0
    y_um: float = 0.0
    moving: bool = False


@app.startup
def connect_stage() -> Stage:
    return Stage(*driver.position())
```

## Keep it in sync

A published state is only worth watching if it is true. Two things change the
world, and both write the state:

**The action that changed it** takes the state by annotation and writes what it
did. Assigning a field publishes it; nothing else is needed.

```python
@app.action
def move_to(stage: Stage, x_um: float, y_um: float) -> None:
    """Moves the stage and waits until it arrives."""
    stage.moving = True
    driver.move(x_um, y_um)
    stage.x_um, stage.y_um, stage.moving = x_um, y_um, False
```

**Whatever changes it outside arkitekt** -- a joystick, the instrument's own
software, drift -- writes it too. The object your startup hook returned *is* the
published state: keep it, and assign to it from wherever the change is noticed,
on any thread.

```python
@app.startup
def connect_stage() -> Stage:
    stage = Stage(*driver.position())
    driver.on_moved(lambda x, y: (setattr(stage, "x_um", x), setattr(stage, "y_um", y)))
    return stage
```

If the device cannot tell you, ask it in a background hook. An unchanged value
publishes nothing, so asking once a second costs one read, not one message.

```python
@app.background
def follow(stage: Stage) -> None:
    while True:
        stage.x_um, stage.y_um = driver.position()
        koil.sleep(1)
```

## What an action returns

What it *made*, never what could be read from state. An acquisition returns the
image; a move returns nothing, because where the stage is now is the state.

| Instead of | Declare |
| --- | --- |
| `get_position()` | `x_um`, `y_um` on a state |
| `is_laser_on()` | `laser_on: bool` on a state |
| `get_exposure()` / `set_exposure()` | `exposure_ms` on a state, and `set_exposure()` writing it |
| `list_objectives()` | `objectives: list[str]` on a state, and `withStateChoices("self.<state>.objectives")` on the parameter that picks one |
| `move_to() -> Position` | `move_to() -> None`, writing the state |

The last row of choices is worth its own line: what an installation *has* (its
objectives, its channels, its pumps) is state too, and a parameter annotated
with `withStateChoices` is a dropdown of it. No enum has to be built for it.

See `examples/microscope_stage.py` and `examples/embedded_host.py`.
