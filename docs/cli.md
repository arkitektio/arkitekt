# The Arkitekt Next CLI

`arkitekt-next` is the command line for building and running Arkitekt **apps**:

- **Build apps** from your Python code — scaffold, run, generate typed clients,
  and call functions (`init`, `run`, `gen`, `manifest`, `inspect`, `call`).
- **Package plugins** — containerize an app into flavours and publish it
  (`plugin`).
- **Join the mesh** — enroll a machine in the private WireGuard network that
  fronts a deployment (`mesh`).
- **Manage your install** — upgrade the SDK, print versions, dump diagnostics
  (`self`).

Standing up an Arkitekt **server** (hub, coordinator, engine) is the job of
[konstruktor](https://github.com/arkitektio/konstruktor) — the CLI and desktop
app for creating and managing deployments.

This page is a reference for the available commands. Every command and
sub-command also ships with `--help`, so you can always discover the exact flags
from the terminal:

```bash
arkitekt-next --help
arkitekt-next run --help
arkitekt-next mesh join --help
arkitekt-next manifest version --help
```

Each `--help` output also links to the matching page in the hosted
documentation. Those links live as constants in
[`arkitekt_next/cli/docs.py`](../arkitekt_next/cli/docs.py) — change
`DOCS_BASE_URL` or a route there and every `--help` epilogue updates with it.

## Commands at a glance

| Command | What it does | Hosted docs |
| :--- | :--- | :--- |
| `init` · `run` · `gen` · `manifest` · `inspect` · `call` | Build, run and deploy apps from your Python code (client SDK). | <https://arkitekt.live/docs/cli> |
| `plugin` | Containerize an app into flavours and publish it. | <https://arkitekt.live/docs/cli/plugin> |
| `mesh` | Join this machine to the deployment's WireGuard mesh. | <https://arkitekt.live/docs/cli/mesh> |
| `self` | Manage the Arkitekt CLI / SDK installation itself. | <https://arkitekt.live/docs/cli/self> |

## Global options

| Option | Description |
| :--- | :--- |
| `--work-dir`, `-w` | The working directory. Defaults to the current directory. The app commands read and write the `.arkitekt_next` project folder relative to this directory, so you can operate on a project without `cd`-ing into it. |

```bash
# Operate on a project located elsewhere without changing directories
arkitekt-next --work-dir ./my-app manifest inspect
```

> **Note:** The app commands operate on a scaffolded app project. Every one of
> them except `init` expects an initialized app; they create the
> `.arkitekt_next` folder if needed and load the manifest from the working
> directory.

---

# App development

The app commands and the `plugin` group are the client-side SDK: they turn your
Python code into an Arkitekt app and package it for distribution. Every command
below operates on the app in the current working directory (see `--work-dir`).

### `init` — Scaffold a new app

Creates a new Arkitekt Next app in the working directory. It writes an
entrypoint file (default `app.py`) seeded from a template and a
`.arkitekt_next/manifest.yaml` describing the app.

```bash
# Interactive — prompts for identifier, author and entrypoint
arkitekt-next init

# Non-interactive — accept all defaults
arkitekt-next init --yes --package-manager pip

# Fully specified
arkitekt-next init myapp \
  --identifier com.example.myapp \
  --version 0.1.0 \
  --author "Jane Doe" \
  --entrypoint app \
  --scopes read --scopes write \
  --package-manager uv
```

Key options:

| Option | Description |
| :--- | :--- |
| `PATH` | Optional sub-directory to create the app in. Defaults to `.`. |
| `--identifier`, `-i` | Unique app identifier in [reverse domain notation](https://en.wikipedia.org/wiki/Reverse_domain_name_notation) (e.g. `com.example.myapp`). |
| `--version`, `-v` | App version. Must follow [semver](https://semver.org/). Defaults to `0.0.1`. |
| `--author` | Shown to users of your app. Defaults to the current OS user. |
| `--entrypoint`, `-e` | Name of the Python entrypoint file (without `.py`). Defaults to `app`. |
| `--template`, `-t` | Starting template: `simple` or `filter`. |
| `--scopes`, `-s` | One or more requested scopes (`read`, `write`). Repeatable. |
| `--package-manager`, `-pm` | `pip` or `uv`. Defaults to `uv` if it is installed, otherwise `pip`. |
| `--with-extra` | Extras to install with `arkitekt-next` when using `uv`. Defaults to `all`. |
| `--yes`, `-y` | Accept all defaults without prompting. |
| `--overwrite-manifest`, `-om` | Overwrite an existing manifest. |
| `--overwrite-app`, `-oa` | Overwrite an existing entrypoint file. |

When `--package-manager uv` is chosen, `uv` must be installed; the CLI runs
`uv init` and `uv add arkitekt-next[all]` for you.

📖 <https://arkitekt.live/docs/cli/init>

### `run` — Run your app locally

Runs your app against a (local or remote) Arkitekt instance.

```bash
# Development mode with hot-reloading
arkitekt-next run dev

# Production mode (no reloading, scalable)
arkitekt-next run prod

# Connect to a specific instance, unattended
arkitekt-next run dev --url http://localhost:8000 --headless
```

| Sub-command | Description |
| :--- | :--- |
| `dev` | Runs the app with auto-reload on code changes. Best for iterating. |
| `prod` | Runs the app without reloading, as it would run inside a container. |

Common options (shared by `dev` and `prod`):

| Option | Description |
| :--- | :--- |
| `--url`, `-u` | The `fakts_next` URL of the Arkitekt instance to connect to. |
| `--builder`, `-b` | The builder used to assemble the app. Defaults to `arkitekt_next.builders.easy`. |
| `--token`, `-t` | A token for the `fakts_next` instance (skips interactive auth). |
| `--instance-id`, `-i` | The instance id to register the app under. |
| `--redeem-token`, `-r` | A redeem token used for unattended authentication. |
| `--headless`, `-h` | Run without opening a browser for authentication. |
| `--log-level`, `-l` | The log level (e.g. `INFO`, `DEBUG`). |

`run dev` additionally accepts `--no-cache`/`-nc` to skip the fakts cache and
`--deep` to watch the whole directory tree for changes.

📖 <https://arkitekt.live/docs/cli/run>

### `manifest` — Manage the app manifest

The manifest describes the app — its identifier, version, author and the
**scopes** (rights) it requests. It is used to authenticate the app with the
platform.

```bash
arkitekt-next manifest inspect               # print the manifest as a table

arkitekt-next manifest version set 1.2.3     # set an explicit version
arkitekt-next manifest version patch         # 1.2.3 -> 1.2.4
arkitekt-next manifest version minor         # 1.2.3 -> 1.3.0
arkitekt-next manifest version major         # 1.2.3 -> 2.0.0
arkitekt-next manifest version prerelease    # 1.2.3 -> 1.2.3-rc.1
arkitekt-next manifest version build         # 1.2.3 -> 1.2.3+build.1

arkitekt-next manifest scopes list           # scopes this app requests
arkitekt-next manifest scopes available      # all scopes the platform offers
arkitekt-next manifest scopes add write      # request additional scopes
arkitekt-next manifest scopes remove write
```

| Sub-command | Effect |
| :--- | :--- |
| `inspect` | Prints the current manifest as a table. |
| `version set [VERSION]` | Sets an explicit version. Without an argument, prompts and suggests the next patch. |
| `version patch` | Bumps the patch number — bugfixes and small changes. |
| `version minor` | Bumps the minor number — new, backwards-compatible features. |
| `version major` | Bumps the major number — breaking changes. |
| `version prerelease` | Appends/bumps a prerelease segment (e.g. `-rc.1`). |
| `version build` | Appends/bumps a build segment (e.g. `+build.1`). |
| `scopes list` | Lists the scopes this app requests. |
| `scopes available` | Lists all scopes the platform offers. |
| `scopes add / remove <scope>` | Adds or removes a requested scope. |

Scopes are validated against the platform's known scopes (currently `read` and
`write`); passing an unknown scope fails the command.

📖 <https://arkitekt.live/docs/cli/manifest>

### `gen` — Code generation

Generates fully typed Python code for your GraphQL API documents using
[turms](https://github.com/jhnnsrs/turms). Requires `turms` to be installed.

```bash
arkitekt-next gen init      # scaffold a graphql.config.yaml
arkitekt-next gen compile   # generate code once
arkitekt-next gen watch     # regenerate whenever documents change
```

`gen compile` accepts `--config` to point at a specific GraphQL config file
(defaults to the `graphql.config.yaml` created by `gen init`).

📖 <https://arkitekt.live/docs/cli/gen>

### `inspect` — Inspect your app

Inspects parts of your app. These commands are also used by the Arkitekt server
to introspect your app when it runs in production.

```bash
# Scan for module-level (leaking) variables that are unsafe on reload
arkitekt-next inspect variables

# Emit the app's requirements as JSON
arkitekt-next inspect requirements --pretty

# Emit the full agent manifest (implementations, states, requirements) as JSON
arkitekt-next inspect all --pretty
```

| Sub-command | Description |
| :--- | :--- |
| `variables` | Scans the entrypoint for dangerous global variables that can leak across reloads. |
| `requirements` | Prints the service requirements of the app as JSON. |
| `implementations` | Prints the registered implementations of the app. |
| `services` | Lists the registered service SDKs, their requirements and codegen assets. `--schema <name>` dumps a service's raw GraphQL SDL. |
| `hooks` | Lists the `@init` hooks in run order (with their CLI-only flag). |
| `lifecycle` | Lists the agent's startup, shutdown and background hooks. |
| `all` | Prints the complete agent manifest (implementations, states, locks, requirements, bloks), validated the way the server would validate it. |

The JSON-emitting commands accept `--pretty`/`-p` for indented output and
`--machine-readable`/`-mr` for delimiter-wrapped output consumed by the server.

📖 <https://arkitekt.live/docs/cli/inspect>

### `call` — Call functions in your app

Calls functions defined in your app, either locally (no server needed) or
remotely (through a rekuest server).

```bash
arkitekt-next call remote <function> ...
```

📖 <https://arkitekt.live/docs/cli/call>

---

## `plugin` — Containerize and deploy

`plugin` builds your app into Docker containers and deploys it to an Arkitekt
instance. A single app can declare multiple **flavours** (build recipes) for
different hardware — see [Flavours](flavours.md).

```bash
# Scaffold a default (vanilla) flavour, plus a devcontainer
arkitekt-next plugin init --flavour vanilla --devcontainer

# Add a GPU flavour
arkitekt-next plugin flavour add --flavour gpu --description "CUDA enabled build"

# Attach a hardware selector to a flavour
arkitekt-next plugin selector add gpu --kind cuda --cuda-cores 100

# Validate all flavour Dockerfiles and configs
arkitekt-next plugin validate

# Build, stage and publish
arkitekt-next plugin build
arkitekt-next plugin stage
arkitekt-next plugin publish
```

| Sub-command | Description |
| :--- | :--- |
| `init` | Scaffolds a flavour (Dockerfile + `config.yaml`) and optionally a devcontainer. |
| `flavour add` | Adds another build flavour to the project. |
| `selector add` | Adds a hardware selector (e.g. `cuda`) to a flavour. |
| `validate` | Validates every flavour's Dockerfile and `config.yaml`. |
| `build` | Builds the Docker image(s) for the selected flavour(s). |
| `stage` | Prepares a build for publishing. |
| `publish` | Publishes the built image(s) to a registry and registers them. |

`plugin init` options:

| Option | Description |
| :--- | :--- |
| `--flavour`, `-f` | Name of the flavour to scaffold (e.g. `vanilla`, `gpu`). |
| `--template`, `-t` | Dockerfile template: `vanilla` or `uv`. |
| `--description`, `-d` | Human-readable description stored in the flavour's `config.yaml`. |
| `--arkitekt-version`, `-av` | The `arkitekt-next` version to pin in the generated Dockerfile. |
| `--devcontainer`, `-dc` | Also generate a `.devcontainer/<flavour>/devcontainer.json`. |
| `--overwrite`, `-o` | Overwrite an existing flavour of the same name. |

`plugin build` options:

| Option | Description |
| :--- | :--- |
| `--flavour`, `-f` | The flavour to build. By default **all** flavours are built. |
| `--tag`, `-t` | Tag the resulting image with a specific tag. |
| `--no-inspect`, `-n` | Skip inspection of the app during the build. |
| `--url`, `-u` | The `fakts-next` server to use during inspection. |

`plugin selector add <flavour>` attaches a hardware requirement to a flavour and
accepts `--kind`/`-k` (e.g. `cuda`) plus quantitative selectors such as
`--cuda-cores`/`-cc`, `--frequency`/`-fr` and `--memory`/`-m`. See
[Flavours](flavours.md) for how selectors drive deployment.

📖 <https://arkitekt.live/docs/cli/plugin> · [Flavours guide](flavours.md)

---

# Connectivity

## `mesh` — Join the WireGuard mesh

A deployment can front its services with a private WireGuard mesh (an ionscale
tailnet), so clients reach the services over the mesh instead of the public
internet. The `mesh` commands drive the local `tailscale` binary (falling back to
`sudo` when elevated privileges are required), so
[tailscale](https://tailscale.com/download) must be installed first.

`mesh join` uses a **device-code flow**: this machine requests to join, an
organization member authorizes it on a web page, and the machine receives a
single-use pre-auth key and enrolls.

```bash
# Enroll this machine (opens an authorization page for an org member to approve)
arkitekt-next mesh join --url https://my-deployment.example.org

# Join and expose a local HTTP proxy into the mesh (no TUN / root needed)
arkitekt-next mesh proxy --url https://my-deployment.example.org

# Fetch a TLS certificate for this node
arkitekt-next mesh cert

# Disconnect and deregister this node
arkitekt-next mesh leave
```

| Sub-command | Description |
| :--- | :--- |
| `join` | Enroll this machine via the device-code flow, then run `tailscale up`. |
| `proxy` | Join and run a userspace `tailscaled` exposing a local HTTP (and optional SOCKS5) proxy. Runs in the foreground until Ctrl-C. |
| `cert [DOMAIN]` | Fetch a TLS certificate via `tailscale cert` (defaults to this node's MagicDNS name). |
| `leave` | Log out of the tailnet and deregister the node (`tailscale logout`). |

Shared `join`/`proxy` options include `--url`/`-u` (the Fakts server), `--name`/`-n`
(requested machine name), `--description`, `--ephemeral`, `--tag` (repeatable),
`--expiration` (how long the join code stays valid, default 600s) and
`--open-browser/--no-open-browser`. `proxy` additionally takes `--listen` (HTTP
proxy address) and `--socks5-listen`.

📖 <https://arkitekt.live/docs/cli/mesh>

---

# Managing your install

## `self` — The CLI / SDK itself

Meta commands that act on your local Arkitekt installation rather than on a
specific app or deployment.

```bash
arkitekt-next self version    # print the installed version
arkitekt-next self upgrade    # upgrade the installed Arkitekt SDK packages
arkitekt-next self info       # dump environment diagnostics
```

| Sub-command | Description |
| :--- | :--- |
| `version` | Prints the installed `arkitekt-next` version. |
| `upgrade` | Checks PyPI for newer versions of the Arkitekt ecosystem packages and upgrades the outdated ones using the project's package manager (`uv` or `pip`). |
| `info` | Dumps environment diagnostics (installed versions, package manager, paths). |

📖 <https://arkitekt.live/docs/cli/self>

---

## Typical workflows

Develop and ship an app:

```bash
# 1. Create the app
arkitekt-next init myapp --identifier com.example.myapp --package-manager uv
cd myapp

# 2. Iterate locally
arkitekt-next run dev

# 3. Prepare for distribution
arkitekt-next plugin init --flavour vanilla --devcontainer
arkitekt-next manifest version patch
arkitekt-next plugin build
arkitekt-next plugin publish
```

Stand up a server to run those apps against with
[konstruktor](https://github.com/arkitektio/konstruktor), then (optionally) join
a machine to the deployment's mesh:

```bash
konstruktor hub create
arkitekt-next mesh join --url http://localhost:8000
```

