<p align="center">
  <h1 align="center">arkitekt</h1>
</p>

<p align="center">
  <em>Turn your Python functions into apps you can orchestrate, share, and scale.</em>
</p>

<p align="center">
  <a href="https://codecov.io/gh/jhnnsrs/arkitekt"><img src="https://codecov.io/gh/jhnnsrs/arkitekt/branch/master/graph/badge.svg?token=UGXEA2THBV" alt="codecov"></a>
  <a href="https://pypi.org/project/arkitekt/"><img src="https://badge.fury.io/py/arkitekt.svg" alt="PyPI version"></a>
  <a href="https://pypi.python.org/pypi/arkitekt/"><img src="https://img.shields.io/pypi/pyversions/arkitekt.svg" alt="PyPI pyversions"></a>
  <a href="https://arkitekt.live"><img src="https://img.shields.io/badge/docs-arkitekt.live-blue" alt="Documentation"></a>
</p>

---

## What is Arkitekt?

[**Arkitekt**](https://arkitekt.live) is an open platform for building, connecting, and orchestrating
computational apps. `arkitekt` is its Python client: it takes your ordinary Python functions and
exposes them as **remotely callable, orchestratable building blocks** — without you having to write
servers, APIs, message queues, or UIs.

Declare an app, run it, and its actions become available on an Arkitekt server where they can be:

- **Called** from anywhere — other apps, notebooks, scripts, or the web UI.
- **Composed** into real-time workflows that wire your functions together.
- **Given a GUI automatically**, generated from your Python type hints.
- **Shared** with your team behind central authentication and permissions.
- **Packaged and deployed** as a Docker container with a single command.

Arkitekt grew out of the needs of data-intensive science (it has first-class clients for microscopy,
electrophysiology and graph data), but the core is **domain-agnostic** — any Python workload fits.

> 📚 The best place to understand the platform and its concepts is the documentation at **[arkitekt.live](https://arkitekt.live)**.

## Installation

```bash
pip install "arkitekt[all]"
```

This installs the `arkitekt` command line interface, the runtime and every service client. Prefer a
lean install? The CLI and packaging tooling are always included — pick only the extras you need:

| Extra | Brings in |
| --- | --- |
| `rekuest` | the distributed runtime `run(app)` needs to offer actions |
| `mikro` | microscopy and imaging data |
| `elektro` | electrophysiology data and simulations |
| `kraph` | knowledge graphs and measurements |
| `fluss` | workflows, and the engine that runs them |
| `kabinet` | managing deployments of apps |
| `unlok` | users, clients, hubs and redeem tokens (lok) |
| `alpaka` | LLMs and chat |
| `lovekit` | WebRTC streams and rooms |
| `serve` | serving an app from a FastAPI application (arkitekt-fastapi) |
| `qt` | Qt integration (`arkitekt.qt`) |
| `tqdm` | a `tqdm` that reports progress to the running task |

```bash
pip install "arkitekt[rekuest,mikro]"
```

Declaring, inspecting and packaging an app, and calling services with `easy`, need no runtime; offering
actions with `run(app)` needs the `rekuest` extra. `arkitekt` requires **Python 3.11+**.

## Offering actions

An `App` is a declaration: its identifier, its version, and the actions it offers. Any function
decorated with `@app.action` becomes a callable building block on the platform. Its arguments and
return value are inferred from the type hints, which also drive validation, documentation and the
generated GUI. The function's name becomes the action's title (`greet` is "Greet"; pass `name=` for another), its docstring the description.

```python
from typing import Annotated

from arkitekt import App, Description, run

app = App("hello", "0.1.0")


@app.action
def greet(
    name: Annotated[str, Description("Who to greet")] = "world",
    times: Annotated[int, Description("How often to say it")] = 1,
) -> str:
    """Says hello."""
    return " ".join([f"Hello {name}!"] * times)


if __name__ == "__main__":
    run(app)
```

Nothing connects when the `App` is declared. `run(app)` authenticates (opening your browser the first
time), registers the actions and blocks until you stop it. The server is taken from `$FAKTS_URL`, or
passed explicitly with `run(app, url="localhost")`; `headless=True` prints a device code instead of
opening a browser.

### State, not getters

Do not offer actions that only read something back (`get_position`, `is_on`). Publish it as a state
and keep it in sync; the UI shows it live and other apps watch it instead of asking:

```python
@app.state
class Stage:
    x_um: float = 0.0
    y_um: float = 0.0


@app.startup
def connect_stage() -> Stage:
    return Stage()


@app.action
def move_to(stage: Stage, x_um: float, y_um: float) -> None:
    """Moves the stage; where it is now is the state."""
    stage.x_um, stage.y_um = x_um, y_um
```

Assigning a field publishes it. An action returns what it made, never what the state already says.
More in [docs/state.md](docs/state.md).

### Beside a program of your own

`run(app)` blocks, which suits a script. A program with its own window, server or threads calls
`run_detached(app, ...)` instead: it returns at once with a run that reports where it stands
(`running.state`, or a `connection_listener`) and is cancelled and started again from any thread.
`device_code_hook` hands the login to your own interface and `task_listener` tells it what remote
callers do. See [docs/embedding.md](docs/embedding.md).

### Using a service inside an action

Actions that need a service client name it in `services=` and take it by annotation — arkitekt injects
the client, just like the running `Task`:

```python
from arkitekt import App, Task, run
from mikro import Mikro, mikro_service
from mikro.arkitekt.specs import Volume

app = App("inspect-volume", "0.1.0", services=[mikro_service])


@app.action
def describe(volume: Volume, mikro: Mikro, task: Task) -> str:
    """Describe Volume"""
    task.progress(50, "Reading")
    return f"{volume.data.shape}"


if __name__ == "__main__":
    run(app)
```

Beyond actions, an app can declare `@app.model` result types, `@app.state` that the platform publishes
live, `@app.startup`/`@app.shutdown` hooks and `@app.background` tasks, and a typed app context
(`App(..., app_context=Setup)` together with `run(app, context=Setup(...))`). The
[examples](examples/README.md) show one each.

### Workflows: actions that call other apps

Only a **workflow** may call other actions. Name what it needs of another app as a protocol with
`@app.declare`, and take it by annotation; the platform resolves it to a running agent of that app:

```python
from typing import AsyncGenerator, Protocol

from arkitekt import App, Task, run

app = App("shouter", "0.1.0")


@app.declare(app="testo", auto_resolvable=True, min=1)
class Testo(Protocol):
    async def stream_words(self, text: str) -> AsyncGenerator[str, None]:
        """Stream Words"""
        ...


@app.workflow
async def shout_words(testo: Testo, text: str, *, task: Task) -> AsyncGenerator[str, None]:
    """Shout Words"""
    async for word in testo.stream_words(text=text):  # streams every yield
        yield word.upper()


if __name__ == "__main__":
    run(app)
```

A workflow is called like any action, and it is the one kind of action that survives its agent
dying: it is **resumed**, and the calls it already made return their recorded results rather than
running again. A plain action whose agent dies ends **LOST** instead, and `call` raises `AgentLost`
with what is known, for whoever called to decide. `effects=` on an action or an `App` says what running
it again would do (`Effects.NONE` … `Effects.IRREVERSIBLE`), as information for that decision. Inside
a workflow, `task.retry`, `task.hold` and `task.guard` cover the usual answers to a lost step:
[examples/recovery](examples/recovery/README.md) walks through them.

## Calling services

Scripts and notebooks that only *call* the platform don't declare actions. `easy` declares an app for
you, connects it, and hands back the clients of the services you name:

```python
from arkitekt import easy
from mikro import mikro_service

with easy("my-script", mikro_service) as mikro:
    folder = mikro.create_folder(name="examples")
```

Name several services and you get a tuple back, in the same order:

```python
from arkitekt import aeasy, interactive
from fluss import fluss_service
from mikro import mikro_service

async with aeasy("my-script", mikro_service, fluss_service) as (mikro, fluss):
    ...

# In Jupyter: connects once and stays connected.
mikro = interactive("notebook", mikro_service)
```

Every service client exposes each operation as a method, in a blocking and an `a`-prefixed async
flavour (`mikro.create_folder(...)`, `await mikro.acreate_folder(...)`).

### Services on the deployment's mesh

Some deployments serve services only over their private mesh. With `pip install "arkitekt[mesh]"`
those services resolve like any other: the login asks the server for a key to join the mesh with,
and a mesh node starts only when a service is reachable no other way. Whether a key comes is up to
the server — you can opt out of the mesh there, and an organization without one grants none;
mesh-only services are then simply not reachable.

```bash
ARKITEKT_MESH=0 python my_app.py                                 # never use the mesh
ARKITEKT_MESH=1 python my_app.py                                 # use it, and report what is missing
ARKITEKT_MESH=force python my_app.py                             # use nothing but the mesh
ARKITEKT_MESH_PROXY=http://localhost:1055 python my_app.py       # go through a running `arkitekt mesh proxy`
```

The same in code, which wins over the environment: `run(app, mesh=False)`, `mesh=True` (or
`MeshOptions(...)`), or `easy("my-script", mikro_service, mesh=MeshProxy(url=...))`.

To log in again — another user, or a session that went stale — run `arkitekt login --reauth` in
the app's folder, pass `run(app, reauth=True)`, `--reauth` on a run, or:

```bash
ARKITEKT_REAUTH=1 python my_app.py
```

The fresh session is cached, so the next plain start reuses it. `skip_cache=True` (`--skip-cache`)
instead neither reads nor writes the cache: every start logs in, and the session lives in memory only.

## The CLI

`arkitekt` is the command line for building, running and packaging apps. It works on the app in
the current folder: `arkitekt --help` lists `create` and `self` where there is none, and the rest
once there is. Standing up an Arkitekt server is the job of
[konstruktor](https://github.com/arkitektio/konstruktor).

| Command | What it does |
| --- | --- |
| `create` | Scaffold an app: an entrypoint file that declares it. There is no separate manifest. |
| `run dev` · `run prod` | Run the app — with hot reloading while you develop, or as it runs in a container. |
| `gen` | Generate typed clients. |
| `inspect` | Show what the app would register, without connecting. |
| `call local` · `call remote` | Call one of the app's actions right here, with no server; or an action on the server. |
| `check` | Check that the app is one a run would accept, without running it. |
| `login` · `logout` · `status` | Log the app in this folder in or out, and see whether it is. |
| `plugin` | Containerize the app into flavours and publish it as a deployable plugin. |
| `mesh` | Join this machine to the deployment's private WireGuard mesh. |
| `self` | Manage your install — upgrade the SDK, print versions, dump diagnostics, list saved logins. |

```bash
arkitekt create my-app && cd my-app   # a project: app, tests, flavour, release workflow
arkitekt run dev                      # run it; reloads on save, shows each task it takes
arkitekt call local generate_random_image --online   # try one action: it stores an image
uv run pytest                         # its tests, with no server
```

A save that does not load is reported and the last working version keeps running.
The tests call the app's actions for real, through their ports, without a
deployment: see **[docs/testing.md](docs/testing.md)**.

See the full reference in **[docs/cli.md](docs/cli.md)**, and
[docs/app_types.md](docs/app_types.md) for choosing between a standalone and a plugin app.

## Working with data

Arkitekt serializes and documents standard Python types — `str`, `bool`, `int`, `float`, `Enum`,
`list`, `dict`, and pydantic models or dataclasses declared with `@app.model`. For heavier data
(images, arrays, large objects), the platform follows a **store-by-reference** model: data lives in a
central, scalable store and only a lightweight reference travels between apps. Service clients like
`mikro` and `elektro` provide ready-made structures for this; within one app,
`app.memory_structure(...)` lets arbitrary objects cross actions without leaving the agent.

## Examples

[`examples/`](examples/README.md) holds small, self-contained scripts — one per thing an app can do.
Each declares its dependencies in a PEP 723 header, so there is nothing to install:

```bash
uv run --script examples/hello.py
```

## Documentation & links

- 📚 **Documentation:** [arkitekt.live](https://arkitekt.live)
- 🧰 **CLI reference:** [docs/cli.md](docs/cli.md)
- 🔌 **Embedding an app in a program you already have:** [docs/embedding.md](docs/embedding.md)
- 📡 **State, not getters:** [docs/state.md](docs/state.md)
- 📦 **PyPI:** [pypi.org/project/arkitekt](https://pypi.org/project/arkitekt/)
- 🐙 **Source:** [github.com/jhnnsrs/arkitekt](https://github.com/jhnnsrs/arkitekt)

## License

`arkitekt` is released under the [MIT License](LICENSE).
