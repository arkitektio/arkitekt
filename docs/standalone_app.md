# Standalone App

The standalone app is the easiest way to get started with Arkitekt. It is a
Python script that connects to an Arkitekt instance and offers functionality —
good for development, testing and simple scripts.

## Offering actions

Declare an `App`, register functions on it, and `run` it. `run` connects, offers
the registered functions, and blocks until you stop it.

```python
from arkitekt import App, run

app = App("my.app")


@app.action
def my_function() -> str:
    """Say hello."""
    return "Hello from my standalone app!"


if __name__ == "__main__":
    run(app)  # offers `my_function` until interrupted
```

## Calling other apps

`easy` is the other direction: it declares an app from the *services* you name
and hands you their clients. Nothing connects until it is entered, and what you
get back is the clients — one service gives you one client, several give you a
tuple.

```python
from arkitekt import easy
from mikro import mikro_service

with easy("my.app", mikro_service) as mikro:
    dataset = mikro.get_array_dataset("some-id")
```

## Configuration

Both take the same keyword arguments:

- `version` — the app's version (default `"0.0.1"`).
- `url` — the fakts server. Defaults to `--url`, then `$FAKTS_URL`, then the
  public deployment at `https://go.arkitekt.live`.
- `scopes` — the scopes the app requests (default `["openid"]`).
- `author`, `logo` — shown in the UI.
- `mandate_key` — a token to provision a new app with (`--mandate-key`,
  `$FAKTS_MANDATE_KEY`).
- `token` — a previously issued credential, `client_id:refresh_token`
  (`--token`, `$FAKTS_TOKEN`).
- `headless` — print the device-code prompt instead of opening a browser.
- `skip_cache` — neither read nor write the fakts cache: log in, and keep the
  session in memory only.
- `reauth` — log in again even when a session is cached, and cache the new one
  (`--reauth`, `$ARKITEKT_REAUTH`).
- `force` — take over an existing agent connection of this app.
- `allow_insecure_transport` — talk plain http to a server that is not on this
  machine (`--allow-insecure-transport`, `$FAKTS_ALLOW_INSECURE_TRANSPORT`).
  Off, such a server is refused.
- `device_id` — this device's identity (`--device-id`, `$ARKITEKT_DEVICE_ID`,
  then the machine's id).
- `supervisor` — the app that controls this process's lifecycle, e.g. the plugin
  engine that started its container (`--supervisor`, `$ARKITEKT_SUPERVISOR`).
- `mesh` — how to reach mesh-only services (`--mesh`, `$ARKITEKT_MESH_PROXY` /
  `$ARKITEKT_MESH`, then the mesh when it is available).

### Where an option comes from

Each option the deployment may set from outside takes a value, `None`, or a
*source*. A value is used as it is; `None` is none (nothing is used or looked up).
A source says where to look, in order: `"arg"` is the flag on the command line,
`"env"` the environment variable, `"default"` the built-in fallback. Any in-order
part of `"arg-env-default"` is a source, and `"discover"` — every option's
default — is all of it:

```python
run(app)  # --supervisor, $ARKITEKT_SUPERVISOR, none
run(app, supervisor="plugin_engine")  # this value
run(app, supervisor=None)  # none, whatever the environment says
run(app, token="env")  # only $FAKTS_TOKEN
run(app, device_id="default")  # the machine's id, ignoring the environment
```

A program with a life of its own (a GUI, a control program) does not call `run`,
which blocks: it calls `run_detached(app, ...)` with the same arguments. See
[Embedding an app](embedding.md).

### Several apps in one process

`run_all(a, b, c)` (and `arun_all` inside a running loop) provides several apps
at once, each as its own agent with its own login:

```python
from arkitekt import run_all

run_all(robot_app, microscope_app, protocol_app, headless=True)
```

They connect in no order. What an app depends on is bound when one of its
tasks is assigned, not when it registers, so a dependent app may register
before its providers. Only a call has to wait for them, and `providing` is the
way to make one: its block is entered once every app is registered, with each
app's runtime (`running[app]`), and leaving it stops the apps.

```python
from arkitekt import providing

async with providing(robot_app, microscope_app, protocol_app, timeout=30) as running:
    rekuest = running[protocol_app].require(RekuestCaller)
    await rekuest.acall(process_slides, loaded_slides=slides)
    await running.wait()  # go on serving until stopped
```

`running.wait()` returns once every app has stopped; without it the apps are
stopped when the block ends.

One app is started the same way in two steps: `await runtime.astart()` returns
when its agent is registered, `await runtime.aloop()` then serves it
(`runtime.arun()` is the two in a row).

When one of the apps depends on another (a protocol declared with
`@app.declare(app="robot")`), `check=True` compares what it demands with what
the other declares before anything logs in, and refuses to start a set that
does not fit. The same comparison is `check_apps(a, b, c)` in code and
`arkitekt check protocol.py --with robot.py` on the command line. A dependency
on an app that is not given is never an error: it is simply not checked.

For those, and for the last word, ask the server once the apps are registered:
`await running.check()` has it resolve every action's dependencies as an assign
would, among all the agents it knows, and returns what it would refuse, with
the reason.

Every app needs its own identifier, and each asks for its own approval the
first time; the prompts say which app they are for. One app failing stops the
others. Apps that need no identity of their own are better merged into one
(`merge`): one agent, one login.

The identifier defaults to the calling file's name, so `easy()` with no
arguments works for a quick script.

## From a script to a plugin

A standalone app and a [plugin app](plugin_app.md) declare the same `App`. What a
script lacks is the project around it:

- **No image**: nothing says how to build it. `arkitekt plugin flavour add` adds a
  flavour (a Dockerfile) to the folder.
- **No release**: nothing publishes it. `arkitekt plugin ci github` adds the
  workflow that does, on every push.
- **Started by hand**: you run the script (`python my_app.py`), or
  `arkitekt run dev my_app` for reloading while you work on it.

`arkitekt create` sets all of that up for a new app; see [Plugin App](plugin_app.md).
