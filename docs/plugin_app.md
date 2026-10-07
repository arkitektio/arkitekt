# Plugin App

A plugin app is an app that is built into a container image and released, so any
Arkitekt deployment can install and run it. It is the same `App` object a
standalone script declares; what makes it a plugin is the project around it: a
flavour to build it from, and a workflow that releases it.

## Create

```bash
arkitekt create my-app
cd my-app
```

You are asked for an identifier (e.g. `com.example.myapp`), an author and the
entrypoint. The new folder holds:

- a [uv](https://docs.astral.sh/uv/) project with `arkitekt` installed,
- `app.py`, seeded from a starter. The app declares itself there: identifier,
  version, what it offers. There is no manifest file to keep in step with it.
  The starter of a project makes a random image and blurs one, storing both in
  mikro (`--starter simple` or `filter` for one that needs no service),
- `tests/`, with two test files for the starter ([Testing an app](testing.md)):
  `test_app.py` needs no server and is what `uv run pytest` runs;
  `test_app_hub.py` runs its actions against a hub made for the tests, with
  `uv run pytest -m hub`,
- `.arkitekt/flavours/vanilla/` (a `Dockerfile` and its `config.yaml`),
- `.github/workflows/release.yaml`, which releases the app on every push, and
  the `[tool.semantic_release]` section of `pyproject.toml` it reads.

Each part has its own option (`--package-manager`, `--tests/--no-tests`,
`--flavour/--no-flavour`, `--ci github|gitlab|none`, `--starter`); see
[the CLI reference](cli.md#create--scaffold-a-new-app).

## Develop

```bash
arkitekt run dev                              # run it, reload on every save
arkitekt call local generate_random_image --online   # try one action: it stores an image
arkitekt check                                # is it an app a run would accept?
uv run pytest                                 # its tests, with no server
```

`run dev` connects to the deployment named by `--url` (or `$FAKTS_URL`), logs in
through the browser the first time, and registers the app's actions there. It
reloads when any Python file in the folder changes; a save that does not load is
reported and the last working version keeps running. Each task the app takes is
shown with how it ended.

`call local` needs no running app: it starts the app for itself and calls the
action in-process. [Testing an app](testing.md) describes the same mechanism
for tests.

## Build locally

```bash
arkitekt plugin build        # build each flavour into an image, and inspect it
arkitekt plugin validate     # check the flavours' Dockerfiles
```

A flavour is one way of building the app: `vanilla` for a plain image, others for
a GPU or another base. `arkitekt plugin flavour add` adds one and
`arkitekt plugin selector add` says where it may be placed
([Flavours](flavours.md)).

## Release

Releasing is what the workflow does, on every push:

```bash
arkitekt plugin release --repository ghcr.io/<org>/<app>
```

It runs the project's tests, builds every flavour for its platforms, runs the
built image to read back what it declares, and pushes the images and a release
descriptor to the OCI repository. Nothing is published if any step fails.

- A commit tagged `v<version>`, where `<version>` is the one the App declares, is
  a **release**: immutable, published as that version.
- Any other commit is a build of its branch's **channel**, versioned
  `<version>-dev.<commit>`.

On GitHub you do not tag by hand. The workflow runs
[semantic-release](https://python-semantic-release.readthedocs.io) before it
publishes, which reads the commits since the last release as
[conventional commits](https://www.conventionalcommits.org): a `fix:` is a patch,
a `feat:` a minor, a `feat!:` a major. If there is one, it raises `__version__`
in `app.py`, commits and tags that, and the workflow publishes the commit as
that release. A push without one is a channel build. Pull the version's commit
before you go on: the branch has moved.

The version is raised in `app.py` and nowhere else; `[tool.semantic_release]` in
`pyproject.toml` says so, and names the branch that releases. A GitLab project
still tags its releases by hand.

A deployment's kabinet then *imports* the repository (`ghcr.io/<org>/<app>`) and
lists its releases; the workflow never talks to a deployment. On GitHub, a
package a workflow creates is private until you make it public.

`arkitekt plugin ci github|gitlab` writes the workflow into a project that has
none. For GitHub the app has to keep its version in a variable semantic-release
can raise: `__version__ = "1.2.3"`, and `App("...", __version__)`.

## Summary

1. `arkitekt create my-app`: the project.
2. `arkitekt run dev`, `arkitekt call local`, `uv run pytest`: write it.
3. `git push`: the workflow tests, builds and publishes it.
4. Commit a `fix:` or a `feat:` to release the next version.
