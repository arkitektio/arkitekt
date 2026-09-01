# The Arkitekt Next CLI

`arkitekt-next` is **the** command line for all things Arkitekt. A single tool now
spans the whole lifecycle of the platform — it absorbed the standalone
`arkitekt-server` tool, so you no longer reach for a second binary to stand up a
deployment:

- **Build apps** from your Python code — scaffold, run, generate typed clients,
  and call functions (`app`).
- **Package plugins** — containerize an app into flavours and publish it
  (`plugin`).
- **Run the server** — bring up the data/compute services, an auth coordinator,
  or the full stack (`hub`, `coord`, `hubinator`, `engine`).
- **Join the mesh** — enroll a machine in the private WireGuard network that
  fronts a deployment (`mesh`).
- **Manage your install** — upgrade the SDK, print versions, dump diagnostics
  (`self`).

This page is a reference for the available command groups. Every command and
sub-command also ships with `--help`, so you can always discover the exact flags
from the terminal:

```bash
arkitekt-next --help
arkitekt-next app --help
arkitekt-next hub init --help
arkitekt-next app manifest version --help
```

Each `--help` output also links to the matching page in the hosted
documentation. Those links live as constants in
[`arkitekt_next/cli/docs.py`](../arkitekt_next/cli/docs.py) — change
`DOCS_BASE_URL` or a route there and every `--help` epilogue updates with it.

## Command groups at a glance

| Group | What it does | Hosted docs |
| :--- | :--- | :--- |
| `app` | Build, run and deploy apps from your Python code (client SDK). | <https://arkitekt.live/docs/cli/app> |
| `plugin` | Containerize an app into flavours and publish it. | <https://arkitekt.live/docs/cli/plugin> |
| `hub` | Run a stack of Arkitekt services trusting an external coordinator. | <https://arkitekt.live/docs/cli/hub> |
| `coord` | Run a coordinator: the Lok auth server + Kontrol frontend. | <https://arkitekt.live/docs/cli/coord> |
| `hubinator` | Run the full stack — a hub **and** a local coordinator. | <https://arkitekt.live/docs/cli/hubinator> |
| `engine` | Run a standalone deployer that orchestrates app containers. | <https://arkitekt.live/docs/cli/engine> |
| `mesh` | Join this machine to the deployment's WireGuard mesh. | <https://arkitekt.live/docs/cli/mesh> |
| `self` | Manage the Arkitekt CLI / SDK installation itself. | <https://arkitekt.live/docs/cli/self> |

## Global options

| Option | Description |
| :--- | :--- |
| `--work-dir`, `-w` | The working directory. Defaults to the current directory. The `app` group reads and writes the `.arkitekt_next` project folder relative to this directory; the server groups (`hub`, `coord`, `hubinator`, `engine`) read and write their deployment config here. Either way you can operate on a project without `cd`-ing into it. |

```bash
# Operate on a project located elsewhere without changing directories
arkitekt-next --work-dir ./my-app app manifest inspect
```

> **Note:** The `app` group operates on a scaffolded app project. Every `app`
> subcommand except `app init` expects an initialized app; it will create the
> `.arkitekt_next` folder if needed and load the manifest from the working
> directory. The server groups (`hub`, `coord`, `hubinator`, `engine`) do **not**
> need an app project — they read and write their own deployment config profile
> instead.

---

# App development

The `app` and `plugin` groups are the client-side SDK: they turn your Python code
into an Arkitekt app and package it for distribution.

## `app` — Build, run and deploy apps

Everything below lives under `arkitekt-next app …` and operates on the app in the
current working directory (see `--work-dir`).

### `app init` — Scaffold a new app

Creates a new Arkitekt Next app in the working directory. It writes an
entrypoint file (default `app.py`) seeded from a template and a
`.arkitekt_next/manifest.yaml` describing the app.

```bash
# Interactive — prompts for identifier, author and entrypoint
arkitekt-next app init

# Non-interactive — accept all defaults
arkitekt-next app init --yes --package-manager pip

# Fully specified
arkitekt-next app init myapp \
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

### `app run` — Run your app locally

Runs your app against a (local or remote) Arkitekt instance.

```bash
# Development mode with hot-reloading
arkitekt-next app run dev

# Production mode (no reloading, scalable)
arkitekt-next app run prod

# Connect to a specific instance, unattended
arkitekt-next app run dev --url http://localhost:8000 --headless
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

### `app manifest` — Manage the app manifest

The manifest describes the app — its identifier, version, author and the
**scopes** (rights) it requests. It is used to authenticate the app with the
platform.

```bash
arkitekt-next app manifest inspect               # print the manifest as a table

arkitekt-next app manifest version set 1.2.3     # set an explicit version
arkitekt-next app manifest version patch         # 1.2.3 -> 1.2.4
arkitekt-next app manifest version minor         # 1.2.3 -> 1.3.0
arkitekt-next app manifest version major         # 1.2.3 -> 2.0.0
arkitekt-next app manifest version prerelease    # 1.2.3 -> 1.2.3-rc.1
arkitekt-next app manifest version build         # 1.2.3 -> 1.2.3+build.1

arkitekt-next app manifest scopes list           # scopes this app requests
arkitekt-next app manifest scopes available      # all scopes the platform offers
arkitekt-next app manifest scopes add write      # request additional scopes
arkitekt-next app manifest scopes remove write
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

### `app gen` — Code generation

Generates fully typed Python code for your GraphQL API documents using
[turms](https://github.com/jhnnsrs/turms). Requires `turms` to be installed.

```bash
arkitekt-next app gen init      # scaffold a graphql.config.yaml
arkitekt-next app gen compile   # generate code once
arkitekt-next app gen watch     # regenerate whenever documents change
```

`gen compile` accepts `--config` to point at a specific GraphQL config file
(defaults to the `graphql.config.yaml` created by `gen init`).

📖 <https://arkitekt.live/docs/cli/gen>

### `app inspect` — Inspect your app

Inspects parts of your app. These commands are also used by the Arkitekt server
to introspect your app when it runs in production.

```bash
# Scan for module-level (leaking) variables that are unsafe on reload
arkitekt-next app inspect variables

# Emit the app's requirements as JSON
arkitekt-next app inspect requirements --pretty

# Emit the full agent manifest (implementations, states, requirements) as JSON
arkitekt-next app inspect all --pretty
```

| Sub-command | Description |
| :--- | :--- |
| `variables` | Scans the entrypoint for dangerous global variables that can leak across reloads. |
| `requirements` | Prints the service requirements of the app as JSON. |
| `implementations` | Prints the registered implementations of the app. |
| `all` | Prints the complete agent manifest (implementations, states, locks, requirements, bloks). |

The JSON-emitting commands accept `--pretty`/`-p` for indented output and
`--machine-readable`/`-mr` for delimiter-wrapped output consumed by the server.

📖 <https://arkitekt.live/docs/cli/inspect>

### `app call` — Call functions in your app

Calls functions defined in your app, either locally (no server needed) or
remotely (through a rekuest server).

```bash
arkitekt-next app call remote <function> ...
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

# Server deployment

These groups stand up an Arkitekt deployment. They were migrated from the
standalone `arkitekt-server` tool, so the whole platform is now driven from one
CLI. None of them need an app project — each `init` writes a deployment config
profile into the working directory, and each `up` composes that profile and
starts it.

All four groups are generated from one registry, so they share the same
lifecycle:

| Command | What it does |
| :--- | :--- |
| `init` | Write the deployment config profile (the source of truth). |
| `up` | Regenerate the compose/config files from the profile, then start the stack. Pass `--wait` to block until every service is healthy. |
| `down` | Stop the stack and remove its containers. Volumes are **kept** unless you pass `--volumes`. |
| `logs` | Stream service logs (`logs lok`, or all services by default; `--no-follow`, `--tail N`). |
| `status` | Show each service's published port and health. Not available for `engine`, which deploys no gateway. |

Because `up` regenerates from the profile every time, editing the profile YAML
and re-running `up` is how you apply a configuration change.

## Which one do I run?

An Arkitekt deployment is made of a few roles. Pick the group that matches how
much of the stack you want this machine to run:

| Group | Runs the services? | Runs the coordinator (Lok auth + Kontrol)? | Runs a deployer? | Use it when… |
| :--- | :--- | :--- | :--- | :--- |
| `coord` | ✗ | ✓ | ✗ | You want a standalone identity/auth server that hubs and clients authenticate against. |
| `hub` | ✓ | ✗ (trusts an external `coord`) | ✗ | You want the data/compute services but let another machine handle identity. |
| `hubinator` | ✓ | ✓ | optional | You want a self-contained, all-in-one instance (the default the old `arkitekt-server` produced). |
| `engine` | ✗ | ✗ | ✓ | You want a standalone deployer that orchestrates app containers on behalf of an existing deployment. |

The common shape is `init` (write config) then `up` (compose and start):

```bash
arkitekt-next hubinator init      # or: hub / coord / engine
arkitekt-next hubinator up --wait # start, and block until healthy
arkitekt-next hubinator status    # what is running, and is it healthy?
arkitekt-next hubinator logs lok  # follow one service's logs
arkitekt-next hubinator down      # stop it again (keeps your data)
```

Every `init` accepts `--backend` (`docker`, `podman`, `kubernetes`) and, where
relevant, `--port` / `--ssl-port` to set the exposed HTTP/HTTPS ports.

## `hubinator` — Full stack (hub + coordinator)

A self-contained Arkitekt instance: the data/compute services **plus** a local
Lok coordinator (with the Kontrol frontend) and, optionally, a deployer. This is
the all-in-one deployment the standalone `arkitekt-server` tool produced by
default.

```bash
arkitekt-next hubinator init                 # default template
arkitekt-next hubinator init --wizard        # interactive configuration
arkitekt-next hubinator init --template dev  # stable | dev | default | minimal
arkitekt-next hubinator up
```

| Option (on `init`) | Description |
| :--- | :--- |
| `--template`, `-t` | Config template: `stable`, `dev`, `default`, `minimal`. Defaults to `default`. |
| `--wizard`, `-w` | Run the interactive configuration wizard. |
| `--default`, `-d` | Accept all defaults (skip the wizard, no prompts). |
| `--service`, `-s` | Enable exactly these services (repeatable). Defaults to the template's selection. |
| `--rekuest-server` | Rekuest (provenance) server host. `local` (default) runs rekuest as a core dependency. |
| `--port` / `--ssl-port` | Exposed HTTP / HTTPS port. |
| `--backend` | Deployment backend (`docker`, `podman`, `kubernetes`). |

📖 <https://arkitekt.live/docs/cli/hubinator>

## `hub` — Services trusting an external coordinator

Bundles the data/compute services (rekuest, mikro, fluss, …) but runs **no** local
coordinator — it trusts an external coordination (auth) server for identity. It
manages no organizations or users and ships no deployer.

```bash
arkitekt-next hub init --coord-server https://auth.example.org
arkitekt-next hub up
arkitekt-next hub connect      # register the hub's services with an organization
```

| Option (on `init`) | Description |
| :--- | :--- |
| `--template`, `-t` | Config template (`stable`, `dev`, `default`, `minimal`). Omit to run the wizard. |
| `--wizard`, `-w` | Force the interactive configuration wizard. |
| `--default`, `-d` | Accept all defaults (skip the wizard). |
| `--service`, `-s` | Enable exactly these services (repeatable). |
| `--coord-server` | External coordination (auth) server whose JWKS the services trust. |
| `--rekuest-server` | Rekuest (provenance) server host (`local` runs rekuest as a core dependency). |
| `--port` / `--ssl-port` | Exposed HTTP / HTTPS port. |
| `--backend` | Deployment backend (`docker`, `podman`, `kubernetes`). |

`hub connect` inspects the machine's host addresses, advertises each enabled hub
service, and registers them with an organization's coordination server (opening a
browser to authorize). Useful options: `--server` (override the coordinator),
`--all-hosts`/`-a` (advertise every discovered host without prompting),
`--no-browser`, and `--timeout`.

📖 <https://arkitekt.live/docs/cli/hub>

## `coord` — Coordinator (Lok auth + Kontrol)

Runs just the coordinator: the Lok auth server (OIDC/JWKS identity) and the
Kontrol web frontend that clients and hubs authenticate against. It runs no
data/compute services and no deployer — point one or more `hub`s at it via their
`--coord-server`.

```bash
arkitekt-next coord init             # runs the wizard (asks about organizations)
arkitekt-next coord init --default   # accept defaults, no prompts
arkitekt-next coord up
```

| Option (on `init`) | Description |
| :--- | :--- |
| `--template`, `-t` | Config template (`stable`, `dev`, `default`, `minimal`). Omit to run the wizard. |
| `--wizard`, `-w` | Force the interactive configuration wizard. |
| `--default`, `-d` | Accept all defaults (skip the wizard). |
| `--port` / `--ssl-port` | Exposed HTTP / HTTPS port. |
| `--backend` | Deployment backend (`docker`, `podman`, `kubernetes`). |

With no `--template`, the wizard runs and asks whether to set up organizations.

📖 <https://arkitekt.live/docs/cli/coord>

## `engine` — Standalone deployer

An engine is a deployer running on its own docker-compose. It connects to an
existing Arkitekt deployment (a `hub`, `coord` or `hubinator`) and orchestrates
app containers on its behalf. Only the `hubinator` bundles a deployer inline;
everywhere else you run an engine.

```bash
arkitekt-next engine init \
  --url https://my-deployment.example.org \
  --redeem-token <token> \
  --network arkitekt_default
arkitekt-next engine up
```

| Option (on `init`) | Description |
| :--- | :--- |
| `--url` | Gateway URL of the Arkitekt deployment to connect to. |
| `--redeem-token` | Redeem token issued by the target deployment. |
| `--network` | Docker network to join (the target deployment's internal network). |
| `--organization` | Organization the deployer acts on behalf of. |
| `--instance-id` | Instance ID for the deployer. |
| `--backend` | Deployment backend (`docker`, `podman`, `kubernetes`). |

📖 <https://arkitekt.live/docs/cli/engine>

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
arkitekt-next app init myapp --identifier com.example.myapp --package-manager uv
cd myapp

# 2. Iterate locally
arkitekt-next app run dev

# 3. Prepare for distribution
arkitekt-next plugin init --flavour vanilla --devcontainer
arkitekt-next app manifest version patch
arkitekt-next plugin build
arkitekt-next plugin publish
```

Stand up a self-contained server to run those apps against:

```bash
# 1. Bring up an all-in-one deployment
arkitekt-next hubinator init --wizard
arkitekt-next hubinator up

# 2. (Optional) join a machine to the deployment's mesh
arkitekt-next mesh join --url http://localhost:8000
```

---

# Testing against a real server

Installing `arkitekt-next` also installs a pytest plugin, so any project can test
against a real, throwaway Arkitekt deployment without writing fixture code. The
fixtures spin up a stack with [dokker](https://github.com/jhnnsrs/dokker), wait
for it to report healthy, and tear it down (volumes included) afterwards.

```python
def test_my_app(running_app):
    """`running_app` is an app already logged in to a running server."""
    assert running_app.app.services
```

| Fixture | What you get |
| :--- | :--- |
| `arkitekt_server` | A **factory** — call it to boot a stack with the services and kind you want. |
| `running_server` | A full stack with the default services (`rekuest`, `mikro`, `kabinet`). |
| `lok_server` | A lok-only stack. Much faster to boot; use it for auth/coordination tests. |
| `running_app` | An `easy()` app connected to `running_server`, with the device-code login already approved. |

The factory takes the same arguments as `temp_setup`, so a test can ask for
exactly the stack it needs:

```python
def test_against_a_coordinator(arkitekt_server):
    coord = arkitekt_server(kind="coord")           # lok only
    hub = arkitekt_server(["rekuest"], kind="hub")  # services, no local lok
```

Requires a running Docker daemon; tests are skipped automatically without one.
Because booting a stack pulls images and runs migrations, these tests are marked
`integration` and only run when you ask for them:

```bash
pytest -m integration
pytest --arkitekt-channel latest -m integration   # pin the image channel
```

## Seeing why a failure happened

When an assertion fails mid-request, the client-side error rarely says why.
Wrapping the assertion in a watcher attaches the relevant container logs to the
traceback:

```python
def test_upload(running_app):
    with running_app.watch("mikro", "minio"):
        assert upload_something()
```

## Driving the server as an operator

`server.lok` acts as the human who would normally click through the web UI —
approving device codes, authorizing hub registrations, or running any Django
management command inside the lok container:

```python
def test_hub_registration(lok_server):
    code = lok_server.lok.pending_hub_codes()[-1]
    lok_server.lok.approve_hub(code)
```
