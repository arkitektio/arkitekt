# The Arkitekt CLI

`arkitekt` is the command line for building and running Arkitekt **apps**. It
works on **the app in the current folder**, and its menu follows the folder:

| Where you are | `arkitekt --help` lists |
| :--- | :--- |
| A folder with an app | `run` · `login` · `logout` · `status` · `inspect` · `gen` · `call` · `plugin` · `mesh` · `self` |
| Anywhere else | `create` · `self` |

A folder has an app when its entrypoint (`app.py`, or the module named by
`$ARKITEKT_APP`) exists and mentions `arkitekt`. The file is only read, never
imported, to decide this. Nothing is taken away: a command off the list still
runs when you type it, and one that needs an app says so when there is none.

- **Build apps** from your Python code — scaffold, run, generate typed clients,
  and call functions (`create`, `run`, `gen`, `inspect`, `call`).
- **Log in and out** — see and end the saved session of the app in this folder
  (`login`, `logout`, `status`).
- **Package plugins** — containerize an app into flavours and publish it
  (`plugin`).
- **Join the mesh** — enroll a machine in the private WireGuard network that
  fronts a deployment (`mesh`).
- **Manage your install** — upgrade the SDK, print versions, dump diagnostics,
  list the logins saved on this machine (`self`).

Standing up an Arkitekt **server** (hub, coordinator, engine) is the job of
[konstruktor](https://github.com/arkitektio/konstruktor) — the CLI and desktop
app for creating and managing deployments.

This page is a reference for the available commands. Every command and
sub-command also ships with `--help`, so you can always discover the exact flags
from the terminal:

```bash
arkitekt --help
arkitekt run --help
arkitekt mesh join --help
```

Each `--help` output also links to the matching page in the hosted
documentation. Those links live as constants in
[`arkitekt/cli/docs.py`](../arkitekt/cli/docs.py) — change
`DOCS_BASE_URL` or a route there and every `--help` epilogue updates with it.

## Commands at a glance

| Command | What it does | Hosted docs |
| :--- | :--- | :--- |
| `create` · `run` · `gen` · `inspect` · `call` | Build and run apps from your Python code (client SDK). | <https://arkitekt.live/docs/cli> |
| `login` · `logout` · `status` | The saved session of the app in this folder. | <https://arkitekt.live/docs/cli/session> |
| `plugin` | Containerize an app into flavours and publish it. | <https://arkitekt.live/docs/cli/plugin> |
| `mesh` | Join this machine to the deployment's WireGuard mesh. | <https://arkitekt.live/docs/cli/mesh> |
| `self` | Manage the Arkitekt CLI / SDK installation itself. | <https://arkitekt.live/docs/cli/self> |

## Global options

| Option | Description |
| :--- | :--- |
| `--work-dir`, `-w` | The working directory. Defaults to the current directory. The app commands look for the app there, and the menu follows it, so you can operate on a project without `cd`-ing into it. |

```bash
# Operate on a project located elsewhere without changing directories
```

> **Note:** Every app command except `create` expects an app in the working
> directory, and finds it from its own `module[:attr]` target rather than from a
> manifest. Without one it stops with a hint to run `arkitekt create`.

---

# App development

The app commands and the `plugin` group are the client-side SDK: they turn your
Python code into an Arkitekt app and package it for distribution. Every command
below operates on the app in the current working directory (see `--work-dir`).

### `create` — Scaffold a new app

Creates a new Arkitekt app in the working directory: an entrypoint file
(default `app.py`) seeded from a template. The app declares itself in that
file -- there is no manifest to keep in step with it.

```bash
# Interactive — prompts for identifier, author and entrypoint
arkitekt create

# Non-interactive — accept all defaults
arkitekt create --yes --package-manager pip

# Fully specified
arkitekt create myapp \
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
| `--with-extra` | Extras to install with `arkitekt` when using `uv`. Defaults to `all`. |
| `--yes`, `-y` | Accept all defaults without prompting. |
| `--overwrite-app`, `-oa` | Overwrite an existing entrypoint file. |

When `--package-manager uv` is chosen, `uv` must be installed; the CLI runs
`uv init` and `uv add arkitekt[all]` for you.

📖 <https://arkitekt.live/docs/cli/create>

### `run` — Run your app locally

Runs your app against a (local or remote) Arkitekt instance.

```bash
# Development mode with hot-reloading
arkitekt run dev

# Production mode (no reloading, scalable)
arkitekt run prod

# Connect to a specific instance, unattended
arkitekt run dev --url http://localhost:8000 --headless
```

| Sub-command | Description |
| :--- | :--- |
| `dev` | Runs the app with auto-reload on code changes. Best for iterating. |
| `prod` | Runs the app without reloading, as it would run inside a container. |

Both run the App the entrypoint declares (`app = App(...)`); an entrypoint
without one is an error. The connection options are shared by `dev` and `prod`,
grouped in `--help` the same way, and only what you pass is overridden:

| Group | Option | Description |
| :--- | :--- | :--- |
| Server | `--url`, `-u` | The Arkitekt server to connect to (`$FAKTS_URL`). |
| Login | `--token`, `-t` | A previously issued credential, `client_id:refresh_token`: no browser login. |
| Login | `--redeem-token`, `-r` | A redeem token: provisions the app and logs it in without a browser. |
| Login | `--headless` | Print the login link instead of opening a browser. |
| Session | `--reauth` | Log in again and replace the saved session (wrong user or organization). |
| Session | `--skip-cache` | Ignore the saved session and save none: log in, for this run only. |
| Agent | `--force`, `-f` | Take over when another instance of this app is already connected. |
| | `--log-level`, `-l` | The log level (e.g. `INFO`, `DEBUG`). |

`run dev` additionally accepts `--deep` to also watch your installed packages.

After the banner a run says how it got its session and what happens to its
connection, one line each:

```text
◆ Session reused  logged in 3 days ago · `arkitekt logout` ends it
◆ Registered  providing 3 actions
□ Connection lost, reconnecting
◆ Reconnected
```

A failure you can act on is one line too, with what to do about it, rather than
a traceback:

```text
✕ Another instance of this app is already connected  pass --force to take over
```

An App that declares an app context (`App(..., app_context=Config)`) does not run
without one. Both commands take it from your code or from a file:

| Option | Description |
| --- | --- |
| `--context module:attr` | An instance of the declared class, or a zero-argument callable returning one (`--context settings:config`). |
| `--context-file path` | A YAML or JSON mapping validated by the declared class, which must be a pydantic model (`--context-file config.yaml`). |

Either is resolved before anything connects, so a missing or mismatched context
fails at the prompt. `run dev` resolves it again on every reload.

📖 <https://arkitekt.live/docs/cli/run>

### `gen` — Code generation

Generates fully typed Python code for your GraphQL API documents using
[turms](https://github.com/jhnnsrs/turms). Requires `turms` to be installed.

```bash
arkitekt gen compile   # generate code once
arkitekt gen watch     # regenerate whenever documents change
```

`gen compile` accepts `--config` to point at a specific GraphQL config file
(defaults to the `graphql.config.yaml` in the app directory).

📖 <https://arkitekt.live/docs/cli/gen>

### `inspect` — Inspect your app

Inspects parts of your app. These commands are also used by the Arkitekt server
to introspect your app when it runs in production.

```bash
# Scan for module-level (leaking) variables that are unsafe on reload
arkitekt inspect variables

# Emit the app's requirements as JSON
arkitekt inspect requirements --pretty

# Emit the full agent manifest (implementations, states, requirements) as JSON
arkitekt inspect all --pretty
```

| Sub-command | Description |
| :--- | :--- |
| `variables` | Scans the entrypoint for dangerous global variables that can leak across reloads. |
| `requirements` | Prints the service requirements of the app as JSON. |
| `implementations` | Prints the registered implementations of the app. |
| `services` | Lists the service SDKs the app selected, their requirements and codegen assets. `--schema <name>` dumps a service's raw GraphQL SDL. |
| `lifecycle` | Lists the agent's startup, shutdown and background hooks. |
| `all` | Prints the complete agent manifest (implementations, states, locks, requirements, bloks), validated the way the server would validate it. |

The JSON-emitting commands accept `--pretty`/`-p` for indented output and
`--machine-readable`/`-mr` for delimiter-wrapped output consumed by the server.

📖 <https://arkitekt.live/docs/cli/inspect>

### `call` — Call an action on the server

Calls an action available on the connected server and prints what it returns.
The action is named by its hash; without an app argument the call is made as the
`arkitekt-cli` app.

```bash
arkitekt call remote --hash <hash> -a n=41 -a name=bob
```

It takes the same Server, Login and Session options as `run`.

📖 <https://arkitekt.live/docs/cli/call>

---

### `login` · `logout` · `status` — The app's saved session

A login leaves a session behind, saved per app, version and server in your
per-user state directory (not in the project folder). A run logs in by itself
the first time; these commands do it, undo it and show it without running the app.

```bash
arkitekt status            # the app, and whether it is logged in
arkitekt login             # log in now; --reauth replaces a saved session
arkitekt logout            # forget the saved session; the next run logs in again
arkitekt logout --url http://localhost:8000   # ... the one for that server
```

| Command | Description |
| :--- | :--- |
| `status` | Shows the app in this folder and its session: where, since when, and whether it is still usable. |
| `login` | Logs the app in and saves the session. Takes `--url`, `--token`, `--redeem-token`, `--headless`, `--reauth`. |
| `logout` | Forgets the saved session. Local only: nothing is revoked on the server, and an instance of the app that is still running saves its session back. |

Logged in as the wrong user? `arkitekt login --reauth`.

📖 <https://arkitekt.live/docs/cli/session>

---

## `plugin` — Containerize and deploy

`plugin` builds your app into Docker containers and deploys it to an Arkitekt
instance. A single app can declare multiple **flavours** (build recipes) for
different hardware — see [Flavours](flavours.md).

```bash
# Scaffold a default (vanilla) flavour, plus a devcontainer
arkitekt plugin init --flavour vanilla --devcontainer

# Add a GPU flavour
arkitekt plugin flavour add --flavour gpu --description "CUDA enabled build"

# Attach a hardware selector to a flavour
arkitekt plugin selector add gpu --kind cuda --compute-capability 8.6 --vram 8000

# Validate all flavour Dockerfiles and configs
arkitekt plugin validate

# Build, stage and publish
arkitekt plugin build
arkitekt plugin stage
arkitekt plugin publish
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
| `--arkitekt-version`, `-av` | The `arkitekt` version to pin in the generated Dockerfile. |
| `--devcontainer`, `-dc` | Also generate a `.devcontainer/<flavour>/devcontainer.json`. |
| `--overwrite`, `-o` | Overwrite an existing flavour of the same name. |
| `--platform`, `-p` | Platforms this flavour builds for (repeatable). Default: `linux/amd64` and `linux/arm64`. |
| `--no-multi-arch` | Build only for this machine's architecture. |

`plugin build` options:

| Option | Description |
| :--- | :--- |
| `--flavour`, `-f` | The flavour to build. By default **all** flavours are built. |
| `--tag`, `-t` | Tag the resulting image with a specific tag. |
| `--no-inspect`, `-n` | Skip inspection of the app during the build. |
| `--url`, `-u` | The `fakts` server to use during inspection. |
| `--platform`, `-p` | Build these platforms instead of the flavour's (repeatable). |

### Multi-architecture builds

A flavour builds for `linux/amd64` and `linux/arm64` unless it says otherwise, so a plugin runs
both on an x86 server and on an ARM node. The platforms live in the flavour's `config.yaml` and are
chosen when it is scaffolded:

```bash
arkitekt plugin init --no-multi-arch            # this machine only
arkitekt plugin init -p linux/amd64 -p linux/arm64
```

Because a multi-platform image cannot be loaded into the local docker daemon, the work is split:

- `plugin build` builds **every** platform — this machine's is loaded, so it can be inspected,
  tagged and `plugin stage`d, and the others are built to the builder's cache. A dependency with no
  wheel for the other architecture therefore fails here, not after a publish.
- `plugin publish` pushes them as one image (a manifest list), reusing that cache. It rebuilds from
  the current sources, so publish from the tree you built.

Two prerequisites, both reported with the command that fixes them:

- a buildx builder with the `docker-container` driver — the CLI creates one named `arkitekt` on
  first use, since docker's default builder cannot build multiple platforms;
- emulation for the foreign architecture:
  `docker run --privileged --rm tonistiigi/binfmt --install all`.

`--tag` on `plugin build` names this machine's image only; `plugin publish` is what writes the
multi-architecture one.

`plugin selector add <flavour>` attaches a hardware requirement to a flavour.
`--kind`/`-k` picks one of `cpu`, `ram`, `cuda`, `rocm`, `oneapi`, `label`;
`--required/--optional` and `--weight`/`-w` set the hard/soft split. Kind
flags: `--min-count`, `--frequency`/`-fr`, `--arch` (cpu); `--memory`/`-m`
(ram, MB); `--compute-capability`, `--cuda-version`, `--vram`, `--count`,
`--cuda-cores`/`-cc` (cuda, the last deprecated); `--api-version`/`-av`,
`--api-thing`/`-at` (rocm); `--one-api-version`/`-oav` (oneapi); `--key`,
`--value` (label). Services are requirements, never selectors.

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
arkitekt mesh join --url https://my-deployment.example.org

# Join and expose a local HTTP proxy into the mesh (no TUN / root needed)
arkitekt mesh proxy --url https://my-deployment.example.org

# Fetch a TLS certificate for this node
arkitekt mesh cert

# Disconnect and deregister this node
arkitekt mesh leave
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
arkitekt self version    # print the installed version
arkitekt self upgrade    # upgrade the installed Arkitekt SDK packages
arkitekt self info       # dump environment diagnostics
arkitekt self sessions   # every login saved on this machine
```

| Sub-command | Description |
| :--- | :--- |
| `version` | Prints the installed `arkitekt` version. |
| `upgrade` | Checks PyPI for newer versions of the Arkitekt ecosystem packages and upgrades the outdated ones using the project's package manager (`uv` or `pip`). |
| `info` | Dumps environment diagnostics (installed versions, package manager, paths). |
| `sessions` | Lists the logins saved on this machine, of every app. `--forget NAME` forgets one app's (on every server), `--all` every one (`--yes` skips the question). Local only, like `logout`. |

📖 <https://arkitekt.live/docs/cli/self>

---

## Typical workflows

Develop and ship an app:

```bash
# 1. Create the app
arkitekt create myapp --identifier com.example.myapp --package-manager uv
cd myapp

# 2. Iterate locally
arkitekt run dev

# 3. Prepare for distribution
arkitekt plugin init --flavour vanilla --devcontainer
arkitekt plugin build
arkitekt plugin publish
```

Stand up a server to run those apps against with
[konstruktor](https://github.com/arkitektio/konstruktor), then (optionally) join
a machine to the deployment's mesh:

```bash
konstruktor hub create
arkitekt mesh join --url http://localhost:8000
```

