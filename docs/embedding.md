# Embedding an app in a program you already have

`run(app)` blocks until the app stops. That suits a script. A program with a
life of its own -- a control program, a GUI, a server with its own threads --
uses `run_detached` instead. It returns at once with a run the host can watch
and cancel from any thread.

Do not put `run(app)` on a thread of your own: you would have to build what
`run_detached` already is (a way to stop it, to know where it stands, to cancel a
login nobody approved), and the run would be tied to the thread that started it.

```python
from arkitekt import (
    App, ConnectionState, DeviceCodeChallenge, TaskEvent, run_detached,
)

app = App("my-instrument", "1.0.0", app_context=Instrument)


async def on_code(challenge: DeviceCodeChallenge) -> None:
    panel.ask_to_open(challenge.verification_uri_complete, challenge.user_code)

async def on_state(state: ConnectionState) -> None:
    panel.show_connection(state.value)

async def on_task(event: TaskEvent) -> None:
    panel.log(event.action, event.kind.value, event.arguments)


running = run_detached(
    app,
    context=instrument,            # your own object, handed to every action that asks
    url="https://lab.example",
    headless=True,                 # the host shows the login; nothing is printed or opened
    device_code_hook=on_code,
    connection_listener=on_state,
    task_listener=on_task,
)
...
running.cancel()                   # on shutdown, or when the user disconnects
running.start()                    # and connects again, with the same settings
```

## The run

| | |
| --- | --- |
| `running.state` | A `ConnectionState`: `CONNECTING`, `AWAITING_LOGIN`, `REGISTERED`, `DISCONNECTED` (the link dropped and is being retried), `FAILED`, `STOPPED`. |
| `running.error` | What ended it, when it is `FAILED`. |
| `running.cancel()` | Ends a pending login or the run. From any thread; returns when the run stopped. |
| `running.start()` | Runs again after a cancel or a failure. |

`connection_listener` is told every change of `state`, so nothing has to poll.
The listeners and the hook are called on the run's own thread: hand what they
learn over to your interface the way your toolkit wants it (a Qt signal, a
queue, `loop.call_soon_threadsafe`).

To connect to another server, call `run_detached` again: a run keeps the
settings it was started with.

## The login

Without a stored login the run reaches `AWAITING_LOGIN`: `device_code_hook` is
handed a `DeviceCodeChallenge` -- the `user_code`, the `verification_uri_complete`
to open, and `expires_in` seconds -- and the listener is told right after. With
`headless=True` showing it is entirely the hook's; without a hook the prompt is
printed to the terminal.

```python
from arkitekt import has_stored_login, logout

has_stored_login(app, url=url)     # would a run need an approval? Nothing connects.
logout(app, url=url)               # revoke the login on the server and forget it here
```

A login is stored per app identifier, version and server, for the app as it is
declared: changing its version, scopes, description or services is a different
app to the server and logs in again. Give a host's app a version of its own that
changes when its actions do -- not the host program's release number.

`allow_insecure_transport=True` lets a run talk plain http to a server that is
not on this machine (a NAS on the lab network). Off, such a server is refused.

## What remote callers do

`task_listener` is called with a `TaskEvent` for each step of each call:

| `event.kind` | carries |
| --- | --- |
| `ASSIGNED` | `arguments`, as they arrived |
| `PROGRESS` | `progress` (percent), `message` |
| `YIELDED` | -- one per result |
| `DONE` / `FAILED` / `CANCELLED` | `error` on `FAILED` |

Every event has the `task_id` and the `action` it belongs to.

The listeners are awaited where the agent reports, so a slow one holds every
task's reports back. Take the event and return: put it on a queue or emit a
signal, and do the work on your side.

## The host's own object

`App(app_context=Instrument)` and `run_detached(app, context=instrument)` hand
your object to every action and hook that names it by annotation -- no globals,
no closures over `self`:

```python
@app.action
def set_flow(instrument: Instrument, pump: str, ml_per_min: float) -> None:
    instrument.set_flow(pump, ml_per_min)
```

What an installation offers is often only known once the program runs. Each
decorator has a plain call beside it for that:

```python
if instrument.has_dispenser:
    app.register_action(dispense, locks=["instrument"])
```

`register_action`, `register_workflow`, `register_state`, `register_model`,
`register_context`, `register_startup`, `register_background`,
`register_shutdown` and `register_protocol` take the function or class first and
the decorator's options as keywords. What is offered can be listed without
connecting: `app.registry.implementations` maps each interface to its definition
(`.definition.name`, `.definition.description`, `.effects`, `.locks`).

## Stopping a call

A function that is not `async` is only told of a cancellation where it asks:
at `task.check_cancelled()`, `task.progress(...)` and `task.log(...)`. Call
`task.check_cancelled()` between the steps of anything long -- before each move,
each frame -- or a cancelled call runs to its end.

## Showing what the instrument does

Publish it as state rather than offering actions that read it back: see
[State, not getters](state.md). `examples/embedded_host.py` puts all of this
together.
