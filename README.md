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
  <a href="https://pypi.python.org/pypi/arkitekt/"><img src="https://img.shields.io/pypi/status/arkitekt.svg" alt="PyPI status"></a>
  <a href="https://arkitekt.live"><img src="https://img.shields.io/badge/docs-arkitekt.live-blue" alt="Documentation"></a>
</p>

---

## What is Arkitekt?

> **Renamed.** This client was published as `arkitekt-next` up to 1.4.2. From 2.0.0 it
> is published as `arkitekt` again: the import root is `arkitekt` (`arkitekt_next` is
> gone) and the CLI command is `arkitekt`, not `arkitekt-next`. Install `arkitekt>=2`.
> Note the extras changed meaning too — `arkitekt[mikro]` now brings mikro 3.x, and the
> `reaktion` extra is gone (the flow engine lives in `fluss[engine]`).

[**Arkitekt**](https://arkitekt.live) is an open platform for building, connecting, and orchestrating
computational apps. `arkitekt` is its Python client: a framework that takes your ordinary Python
functions and exposes them as **remotely callable, orchestratable building blocks** — without you having
to write servers, APIs, message queues, or UIs.

Annotate a function, run your app, and it becomes available on an Arkitekt server where it can be:

- **Called** from anywhere — other apps, notebooks, scripts, or the web UI.
- **Composed** into real-time workflows that wire your functions together.
- **Given a GUI automatically**, generated from your Python type hints.
- **Shared** with your team behind central authentication and permissions.
- **Packaged and deployed** as a Docker container with a single command.

Arkitekt grew out of the needs of data-intensive science (it has first-class extensions for microscopy,
imaging, and graph data), but the core is **domain-agnostic** — any Python workload fits.

> 📚 The best place to understand the platform and its concepts is the documentation at **[arkitekt.live](https://arkitekt.live)**.

## Installation

```bash
pip install "arkitekt[all]"
```

This installs everything, including the `arkitekt` command line interface used to create, develop,
containerize, and deploy apps.

Prefer a lean install? The CLI and packaging tooling are always included — pick
only the service extras you need:

```bash
pip install "arkitekt[mikro]"          # microscopy / imaging data
pip install "arkitekt[fluss]"          # workflow orchestration
pip install "arkitekt[elektro]"       # electrophysiology data
pip install "arkitekt[alpaka]"         # want to talk to LLMs? This one's for you.
```

`arkitekt` requires **Python 3.11+** and builds on the `asyncio` and `pydantic` stacks.

## Quickstart

### 1. Create an app

```bash
mkdir my-app && cd my-app
arkitekt init
```

This walks you through creating an app and writes a manifest (identifier, version, entrypoint, scopes)
into `.arkitekt/`.

### 2. Register your functions

Any function you decorate with `@register` becomes a callable building block on the platform. Its
arguments and return values are inferred from your type hints — which also drive validation,
documentation, and the auto-generated GUI.

```python
from arkitekt import register


@register
def greet(name: str, excited: bool = False) -> str:
    """Greet a person by name.

    Args:
        name: Who to greet.
        excited: Add some enthusiasm.
    """
    greeting = f"Hello, {name}"
    return greeting + "!" if excited else greeting
```

### 3. Run it

```bash
arkitekt run dev
```

`run dev` connects your app to a local or remote Arkitekt server with **hot reloading** — edit your
code and the app reloads automatically. When you are ready for production, use `arkitekt run prod`.

## The CLI

`arkitekt` is the command line for building and running Arkitekt apps.
Standing up an Arkitekt server is the job of
[konstruktor](https://github.com/arkitektio/konstruktor):

| Command | What it does |
| --- | --- |
| `init` · `run` · `gen` · `manifest` · `inspect` · `call` | Build, run and deploy apps from your Python code — scaffold, run locally (`run dev`/`run prod`), generate typed clients, manage the manifest, inspect, and call functions. |
| `plugin` | Containerize your app into flavours and publish it as a deployable plugin. |
| `mesh` | Join this machine to the deployment's private WireGuard mesh. |
| `self` | Manage your Arkitekt install — upgrade the SDK, print versions, dump diagnostics. |

```bash
arkitekt init         # scaffold an app
arkitekt run dev      # run it with hot reloading
konstruktor hub create         # stand up a server to run it against (separate tool)
```

See the full reference in **[docs/cli.md](docs/cli.md)**.

## Working with data

Arkitekt automatically serializes and documents standard Python types — `str`, `bool`, `int`, `float`,
`Enum`, `list`, and `dict`. For heavier data (images, arrays, large objects), the platform follows a
**store-by-reference** model: data lives in a central, scalable store and only a lightweight reference
travels between apps. Extensions like [`mikro`](https://arkitekt.live) provide ready-made structures for
this, and you can define your own.

See the documentation for details on custom data structures and storage backends.

## Documentation & links

- 📚 **Documentation:** [arkitekt.live](https://arkitekt.live)
- 🧰 **CLI reference:** [docs/cli.md](docs/cli.md)
- 📦 **PyPI:** [pypi.org/project/arkitekt](https://pypi.org/project/arkitekt/)
- 🐙 **Source:** [github.com/jhnnsrs/arkitekt](https://github.com/jhnnsrs/arkitekt)

## License

`arkitekt` is released under the [MIT License](LICENSE).
