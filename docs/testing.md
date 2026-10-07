# Testing an app

Two suites, and they are not run in the same place:

| Suite | Tests | Needs | Runs |
| --- | --- | --- | --- |
| **Unit** | `call`: the app runs for itself, with no server | nothing | while writing, and on every push |
| **End to end** | `hub_call`: the same app, logged in to a hub made for the tests | Docker, a minute, and every service working | on a dedicated runner: nightly, or before a release |

The unit suite is where an app is tested. Every branch of an action's logic
belongs there: it runs in seconds, anywhere, and a failure in it is the app's.

The end-to-end suite answers one question the unit suite cannot: does this app
still work against the real services? It notices a token that is not accepted,
a schema that moved, an agent that no longer registers. Keep it small, a test
or two for each service the app uses, proving the wiring and nothing else. It
is slow to start, and a failure in it may be a service's and not the app's, so
it is not something to run while writing code, and not something a push should
wait for.

## An action, with no server

An action is more than its function. Between a call and the function sit the
ports (arguments expanded, results shrunk), the clients the action is handed, its
task, the app's states and its startup hooks. Calling the function in a test
checks none of that.

`arkitekt.testing` runs the app for itself instead: started as a run starts it,
called through its own agent, with no server anywhere. It needs the runtime
(`arkitekt[rekuest]`, which `arkitekt[all]` includes) and `pytest`.

## With pytest

Load the fixtures in `tests/conftest.py`:

```python
pytest_plugins = ["arkitekt.testing"]
```

A test then asks for `call`, and calls an action by name or by the function:

```python
def test_add(call):
    assert call("add", 1, b=2) == 3
```

`arkitekt create` writes both files for a new project, with tests of the
starter, and adds `pytest` as a dev dependency. Run them with
`uv run pytest`; the release workflow runs them before it builds anything.
A starter that uses a service gets a second file, `tests/test_app_hub.py`, with
the tests that run against a hub (`uv run pytest -m hub`, see below). The
`conftest.py` it writes also puts the project on the path, so a test can
`from app import ...`, and `pyproject.toml` keeps a bare `pytest` to the tests
that need no hub.

`call` returns what the action returned (of a generator, what it yielded last)
and raises `arkitekt.testing.LocalCallError` when the action raises:

```python
import pytest
from arkitekt.testing import LocalCallError

def test_refuses_an_empty_window(call):
    with pytest.raises(LocalCallError, match="at least 1"):
        call("moving_average", values=[1.0], window=0)
```

The fixtures, each of which a project can override in its `conftest.py`:

| Fixture | What it is |
| --- | --- |
| `call` | `call(action, *args, **kwargs)`: one of the app's actions, called in-process. |
| `local_runtime` | The started app, for one test: `call_local`, and `require(Client)` for the client an action would be handed. |
| `arkitekt_app` | The app under test: `$ARKITEKT_APP`, else the module `app` in the folder pytest runs from. |
| `arkitekt_clients` | The clients actions are handed in place of the services' own. Empty by default. |
| `arkitekt_context` | The app context the app is started with, for an app that declares one. |

## End to end: against the real services

Offline, a service of the app builds its real client against an address that does
not exist. The client is there to be handed out, so an action that merely takes
it runs; a call through it fails. That is enough for most of what an action
does: test its logic with `call`, and give it what it would have fetched.

To prove the action against the service itself, ask for `hub_call` in place of
`call`:

```python
import pytest
from mikro import Mikro

@pytest.mark.hub
def test_it_stores_the_result(hub_call, hub_runtime):
    folder = hub_call("make_folder", name="results")

    assert hub_runtime.require(Mikro).get_folder(folder.id).name == "results"
```

`teststack` is the same in one typed fixture: the hub, the app and its run.
Annotate it with the app's context, `TestStack[Config]` for an app declared with
`app_context=Config` and `TestStack[None]` for one without, and a type checker
knows the rest:

```python
import pytest
from arkitekt.testing import TestStack
from mikro import Mikro

@pytest.mark.hub
def test_it_stores_the_result(teststack: TestStack[None]):
    folder = teststack.call("make_folder", name="results")

    assert teststack.runtime.require(Mikro).get_folder(folder.id).name == "results"
```

The first such test starts a hub for the session: the services the app uses,
and a coordination server of its own, in Docker, on a port of its own. It is
made by [konstruktor](https://github.com/arkitektio/konstruktor)
from one thing each service's package declares, the
image that hosts it:

```python
@registry.service(image="jhnnsrs/mikro:7", ...)
def mikro(...) -> Mikro: ...
```

Nothing else is written down anywhere: the image says what it needs, and
konstruktor generates the rest. The app then logs in to that hub the way it logs
in to any deployment, so the action is handed the client the app itself built,
with a token the hub's own server issued. An app that offers actions is served
by rekuest, so its hub runs rekuest too.

| Fixture | What it is |
| --- | --- |
| `teststack` | A `TestStack[Ctx]` for one test: `hub`, `app`, `runtime`, and `call(action, *args, **kwargs)`. |
| `hub_call` | `hub_call(action, *args, **kwargs)`: an action called in-process, its services real. |
| `hub_runtime` | The started app, logged in to the hub, for one test: `require(Client)` is the service's client. |
| `arkitekt_hub` | The hub, for the session: `fakts_url`, `redeem_token(name)`, `logs()`. |
| `arkitekt_hub_apps` | How many apps can log in to it (8): one redeem token serves one app. |

### Where it runs

`@pytest.mark.hub` is registered by `arkitekt.testing`, and is what keeps the two
suites apart:

```bash
uv run pytest -m "not hub"   # the unit suite: the dev loop, every push
uv run pytest -m hub         # end to end: a dedicated runner with Docker
```

Make the first the default, so a bare `uv run pytest` never starts a hub, in
`pyproject.toml`:

```toml
[tool.pytest.ini_options]
addopts = "-m 'not hub'"
```

`uv run pytest -m hub` on the command line still selects the end-to-end suite:
the last `-m` wins.

Run that one from a workflow of its own, on a schedule or before a release, not
from the workflow that gates every push. It pulls the services' images, takes
about a minute to start, and needs a runner with Docker and a few gigabytes of
memory to spare. Where Docker or konstruktor is missing its tests are skipped,
which is not the same as passing: check that the runner reports them as run.

The tests of one session share one hub, so each should make what it asserts on
and not count on the hub being empty.

`KONSTRUKTOR_IMAGES=mikro=jhnnsrs/mikro:next` runs the hub's mikro on another
image than the declared one, to try an app against a server not released yet.

## Without pytest

`local_app` is the same thing as a context manager, for a script, a notebook or
another test runner:

```python
from arkitekt.testing import local_app
from app import app, add

with local_app(app) as rt:
    assert rt.call_local(add, 1, 2) == 3

async with local_app(app) as rt:
    async for value in rt.aiterate_local("count", to=3):
        ...
```

Entering it runs the app's startup hooks, states and background work; leaving it
runs the shutdown hooks. It needs no pytest. An async test uses the `async with`
form, so the app runs on the test's own event loop; the fixtures are for
synchronous tests.

With a service, connect the app to a hub of your own making:

```python
from arkitekt.runtime import connect_local
from arkitekt.testing import service_images
from konstruktor import testing_hub

with testing_hub(service_images=service_images(app)) as hub:
    hub.up()
    hub.wait_ready()
    with connect_local(app, offline=False, url=hub.fakts_url,
                       redeem_token=hub.redeem_token("my-app")) as rt:
        rt.call_local("make_folder", name="results")
    hub.logs("mikro")   # the service's side of it, while the hub is there
```

The hub is gone, with its data, when the block is left. The same `hub` is what the
`teststack.hub` of a test is, so a test can ask it for a service's logs, its
containers (`hub.ps()`) or a command inside one (`hub.exec(...)`).

## What not to do

- **Do not test against a shared deployment**, yours or anybody's. A test that
  fails halfway leaves what it wrote, for everybody who uses that deployment;
  what it passes on depends on what was there before; and nobody else, CI
  included, can run it. A hub made for the session has none of that: it starts
  empty and is gone afterwards. `arkitekt call local --online` and
  `arkitekt run dev` are for trying an app on a deployment by hand, not for its
  tests.
- **Do not write a fake of a service.** A `FakeMikro` answers what its author
  thought mikro answers, and keeps passing when mikro changes. Starting the
  service costs about a minute, once per session.

## What it does not cover

- An action that calls **other apps'** actions (a workflow) has nobody to call
  in a local run: nothing is registered, so no server assigns the call. Run the
  apps for real against the hub instead, each with a token of its own:
  `connect(other, provide=True, url=arkitekt_hub.fakts_url,
  redeem_token=arkitekt_hub.redeem_token("other"))`.
- Nothing is registered, so what the server does with the app's declaration is
  not exercised. `arkitekt check` validates the declaration the way a run does
  before it connects.

From the command line, `arkitekt call local <action> -a key=value` is the same
call, for trying an action while writing it.
