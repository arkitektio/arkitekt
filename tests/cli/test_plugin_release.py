"""``arkitekt plugin release``: what a checkout releases, and where it goes.

The pieces that decide something are tested without docker: what git makes of a
checkout, whether an image may stand for a release, and the registry protocol against
a registry served from this process. One docker-backed test then runs the command
against a real ``registry:2``.
"""

import hashlib
import json
import os
import subprocess
import sys
import threading
import tomllib
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

import pytest
import typer
from arkitekt_spec import AppManifest, Inspection, ReleaseDescriptor, ReleaseFlavour
from typer.testing import CliRunner

from arkitekt.cli.commands.plugin.registry import Repository
from arkitekt.cli.commands.plugin.release import Resolved, check_identity, resolve
from arkitekt.cli.main import cli_app

from .isolation import isolated_filesystem
from .test_build import _scaffold

PINNED = "localhost:1/org/app@sha256:" + "a" * 64


def git(directory: str | Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", *arguments],
        cwd=directory,
        stdout=subprocess.PIPE,
        text=True,
        check=True,
    ).stdout.strip()


@pytest.fixture
def checkout(tmp_path: Path) -> Path:
    git(tmp_path, "init", "-q", "-b", "main")
    (tmp_path / "app.py").write_text("x = 1\n")
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-q", "-m", "first")
    return tmp_path


# -- what a checkout releases -------------------------------------------------


def test_a_branch_commit_is_a_build_of_its_channel(checkout: Path):
    revision = git(checkout, "rev-parse", "HEAD")
    resolved = resolve("1.4.0", str(checkout))
    assert resolved == Resolved(f"1.4.0-dev.{revision[:7]}", "main", revision, None)
    assert resolved.tag == "main"


def test_the_commit_tagged_with_the_apps_version_is_that_release(checkout: Path):
    git(checkout, "tag", "v1.4.0")
    resolved = resolve("1.4.0", str(checkout))
    assert (resolved.version, resolved.channel, resolved.tag) == ("1.4.0", None, "1.4.0")


def test_a_version_tag_the_app_does_not_declare_is_refused(checkout: Path, capsys):
    git(checkout, "tag", "v2.0.0")
    with pytest.raises(typer.Exit):
        resolve("1.4.0", str(checkout))
    assert "the app declares version 1.4.0" in capsys.readouterr().err


def test_a_named_channel_wins_over_the_tag(checkout: Path):
    """A push of a tagged commit to its branch is still a build of the branch."""
    git(checkout, "tag", "v1.4.0")
    resolved = resolve("1.4.0", str(checkout), channel="feat/thing")
    assert resolved.channel == "feat/thing"
    assert resolved.tag == "feat-thing"
    assert resolved.version.startswith("1.4.0-dev.")


def test_a_detached_commit_needs_its_channel_named(checkout: Path, capsys):
    git(checkout, "checkout", "-q", "--detach")
    with pytest.raises(typer.Exit):
        resolve("1.4.0", str(checkout))
    assert "--channel" in capsys.readouterr().err


def test_uncommitted_changes_are_refused(checkout: Path, capsys):
    (checkout / "app.py").write_text("x = 2\n")
    with pytest.raises(typer.Exit):
        resolve("1.4.0", str(checkout))
    assert "uncommitted" in capsys.readouterr().err
    assert resolve("1.4.0", str(checkout), allow_dirty=True).channel == "main"


def test_the_source_never_carries_the_remotes_credentials(checkout: Path):
    git(checkout, "remote", "add", "origin", "https://bot:secret@example.com/org/app.git")
    assert resolve("1.4.0", str(checkout)).source == "https://example.com/org/app.git"


def test_outside_git_there_is_nothing_to_release(tmp_path: Path, capsys):
    with pytest.raises(typer.Exit):
        resolve("1.4.0", str(tmp_path))
    assert "git" in capsys.readouterr().err


# -- whether an image may stand for the release ---------------------------------

MANIFEST = AppManifest(identifier="app", version="1.4.0")
RELEASE = Resolved("1.4.0", None, "abc", None)
CHANNEL = Resolved("1.4.0-dev.abc", "main", "abc", None)


def test_an_image_that_is_the_release_passes():
    check_identity("vanilla", MANIFEST, MANIFEST, RELEASE)


def test_an_older_image_is_taken_at_the_sources_word_for_a_release():
    check_identity("vanilla", None, MANIFEST, RELEASE)


def test_a_channel_build_has_to_say_which_version_it_is(capsys):
    with pytest.raises(typer.Exit):
        check_identity("vanilla", None, MANIFEST, CHANNEL)
    assert "predates channel builds" in capsys.readouterr().err


def test_a_channel_image_still_carrying_the_sources_version_is_refused(capsys):
    with pytest.raises(typer.Exit):
        check_identity("vanilla", MANIFEST, MANIFEST, CHANNEL)
    assert "ARG ARKITEKT_APP_VERSION" in capsys.readouterr().err


def test_an_image_of_another_app_is_refused(capsys):
    other = AppManifest(identifier="other", version="1.4.0")
    with pytest.raises(typer.Exit):
        check_identity("vanilla", other, MANIFEST, RELEASE)
    assert "'other'" in capsys.readouterr().err


def test_the_build_version_wins_over_the_declared_one(monkeypatch):
    from arkitekt import App

    monkeypatch.setenv("ARKITEKT_APP_VERSION", "1.4.0-dev.abc")
    assert App("app", version="1.4.0").version == "1.4.0-dev.abc"
    monkeypatch.setenv("ARKITEKT_APP_VERSION", "")
    assert App("app", version="1.4.0").version == "1.4.0"


# -- the registry protocol ------------------------------------------------------


class _Registry(BaseHTTPRequestHandler):
    """Enough of the distribution API to push and read a release, behind a token."""

    blobs: dict[str, bytes] = {}
    manifests: dict[str, bytes] = {}
    seen_tokens: list[str] = []

    def log_message(self, *arguments: object) -> None:  # pyright: ignore[reportIncompatibleMethodOverride] -- silenced, whatever it is handed
        pass

    def _answer(self, status: int, body: bytes = b"", **headers: str) -> None:
        self.send_response(status)
        for key, value in headers.items():
            self.send_header(key.replace("_", "-"), value)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _handle(self) -> None:
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length)
        path, _, query = self.path.partition("?")
        if path == "/token":
            return self._answer(200, json.dumps({"token": "letmein"}).encode())
        if self.headers.get("Authorization") != "Bearer letmein":
            realm = f"http://{self.headers['Host']}/token"
            return self._answer(
                401, WWW_Authenticate=f'Bearer realm="{realm}",service="test",scope="x:pull,push"'
            )
        kind, _, reference = path.removeprefix("/v2/org/app/").partition("/")
        store = self.manifests if kind == "manifests" else self.blobs
        if self.command in ("GET", "HEAD"):
            if reference not in store:
                return self._answer(404)
            digest = "sha256:" + hashlib.sha256(store[reference]).hexdigest()
            return self._answer(200, store[reference], Docker_Content_Digest=digest)
        if self.command == "POST":
            return self._answer(202, Location="/v2/org/app/blobs/upload-1?state=x")
        digest = "sha256:" + hashlib.sha256(body).hexdigest()
        if kind == "manifests":
            self.manifests[reference] = self.manifests[digest] = body
        else:
            assert query == f"state=x&digest={digest.replace(':', '%3A')}"
            self.blobs[digest] = body
        return self._answer(201, Docker_Content_Digest=digest)

    do_GET = do_HEAD = do_POST = do_PUT = _handle


@pytest.fixture
def repository() -> Iterator[Repository]:
    _Registry.blobs, _Registry.manifests = {}, {}
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Registry)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield Repository(f"127.0.0.1:{server.server_port}", "org/app")
    server.shutdown()


def a_release(**changes: object) -> ReleaseDescriptor:
    return ReleaseDescriptor.model_validate(
        {
            "manifest": MANIFEST,
            "flavours": [ReleaseFlavour(name="vanilla", image=PINNED, inspection=Inspection())],
            **changes,
        }
    )


def test_a_pushed_release_reads_back_as_it_was_pushed(repository: Repository):
    assert not repository.has("1.4.0")
    digest = repository.push_release("1.4.0", a_release(revision="abc"))
    assert repository.has("1.4.0")
    assert repository.manifest_digest("1.4.0") == digest
    assert repository.release("1.4.0") == a_release(revision="abc")


def test_a_tag_that_names_an_image_is_not_a_release(repository: Repository):
    _Registry.manifests["1.4.0-vanilla"] = json.dumps({"manifests": []}).encode()
    assert repository.has("1.4.0-vanilla")
    assert repository.release("1.4.0-vanilla") is None
    assert repository.release("missing") is None


def test_a_channel_tag_moves_to_the_next_build(repository: Repository):
    repository.push_release("main", a_release(channel="main", revision="one"))
    repository.push_release("main", a_release(channel="main", revision="two"))
    release = repository.release("main")
    assert release is not None and release.revision == "two"


# -- the command, against a real registry -----------------------------------------


@pytest.fixture
def docker_registry() -> Iterator[str]:
    container = subprocess.run(
        ["docker", "run", "-d", "--rm", "-p", "127.0.0.1::5000", "registry:2"],
        stdout=subprocess.PIPE,
        text=True,
        check=True,
    ).stdout.strip()
    try:
        port = subprocess.run(
            ["docker", "port", container, "5000/tcp"], stdout=subprocess.PIPE, text=True, check=True
        ).stdout.strip().rsplit(":", 1)[1]
        yield f"localhost:{port}/test/app"
    finally:
        subprocess.run(["docker", "rm", "-f", container], stdout=subprocess.DEVNULL)


@pytest.mark.needs_docker
def test_release_publishes_a_release_and_then_a_channel(docker_registry: str):
    """Build and push for real; only the in-container inspection is canned.

    The image installs the released arkitekt, whose inspection this checkout does not
    promise to read (see test_build.py), so what the container reports is stubbed
    with what a current one would say.
    """
    runner = CliRunner()
    reported: list[AppManifest] = []

    def canned(image: str, target: str, platform: str | None = None):
        assert "@sha256:" in image and image.startswith(docker_registry)
        return Inspection(), reported[-1]

    def release(*extra: str):
        with patch("arkitekt.cli.commands.plugin.release.inspect_image", side_effect=canned):
            return runner.invoke(
                cli_app, ["plugin", "release", "-r", docker_registry, "--no-test", *extra]
            )

    with isolated_filesystem() as directory:
        _scaffold(runner, version="0.0.1")
        git(directory, "init", "-q", "-b", "main")
        git(directory, "add", "-A")
        git(directory, "commit", "-q", "-m", "first")
        git(directory, "tag", "v0.0.1")
        repository = Repository.of(docker_registry)

        reported.append(AppManifest(identifier="com.test.app", version="0.0.1"))
        result = release()
        assert result.exit_code == 0, result.output

        published = repository.release("0.0.1")
        assert published is not None
        assert published.channel is None
        assert published.revision == git(directory, "rev-parse", "HEAD")
        (flavour,) = published.flavours
        assert flavour.name == "vanilla"
        # The descriptor names the very manifest the image tag points at.
        assert flavour.image == repository.pinned(repository.manifest_digest("0.0.1-vanilla") or "")

        # A release never changes.
        result = release()
        assert result.exit_code == 1
        assert "already released" in result.output

        # The next commit is a build of the branch.
        git(directory, "commit", "-q", "--allow-empty", "-m", "second")
        version = f"0.0.1-dev.{git(directory, 'rev-parse', 'HEAD')[:7]}"
        reported.append(AppManifest(identifier="com.test.app", version=version))
        result = release()
        assert result.exit_code == 0, result.output

        channel = repository.release("main")
        assert channel is not None
        assert (channel.channel, channel.manifest.version) == ("main", version)
        assert repository.has(f"{version}-vanilla")
        assert repository.release("0.0.1") == published


# -- the forge's part -----------------------------------------------------------


def test_ci_github_writes_a_workflow_that_versions_and_then_calls_the_action():
    import yaml

    runner = CliRunner()
    with isolated_filesystem() as directory:
        (Path(directory) / "app.py").write_text('__version__ = "0.0.1"\n')
        result = runner.invoke(cli_app, ["plugin", "ci", "github"])
        assert result.exit_code == 0, result.output
        assert "has no __version__" not in result.output
        workflow = yaml.safe_load((Path(directory) / ".github" / "workflows" / "release.yaml").read_text())
        # `on` is YAML for true. The tag is the job's own to make, not a push to wait for.
        assert workflow[True] == {"push": {"branches": ["main"]}}
        job = workflow["jobs"]["release"]
        assert job["permissions"] == {"contents": "write", "packages": "write"}
        checkout, _, test, version, release = job["steps"]
        assert checkout["with"]["fetch-depth"] == 0
        assert test["run"] == "uv run pytest"
        assert version["run"].endswith("semantic-release version")
        assert release["uses"].startswith("arkitektio/arkitekt/ci/github@")
        assert release["with"] == {"target": "app", "release": "${{ steps.version.outputs.released }}"}

        configured = tomllib.loads((Path(directory) / "pyproject.toml").read_text())["tool"]["semantic_release"]
        assert configured["version_variables"] == ["app.py:__version__"]
        assert configured["branches"]["release"]["match"] == "main"

        again = runner.invoke(cli_app, ["plugin", "ci", "github"])
        assert again.exit_code == 1
        assert "already exists" in again.output


def test_ci_github_follows_the_branch_and_the_file_the_app_is_in():
    runner = CliRunner()
    with isolated_filesystem() as directory:
        (Path(directory) / "main.py").write_text('__version__ = "0.0.1"\n')
        result = runner.invoke(cli_app, ["plugin", "ci", "github", "--branch", "trunk", "--entrypoint", "main.py"])
        assert result.exit_code == 0, result.output
        workflow = (Path(directory) / ".github" / "workflows" / "release.yaml").read_text()
        assert "branches: [trunk]" in workflow
        assert "target: main" in workflow
        configured = tomllib.loads((Path(directory) / "pyproject.toml").read_text())["tool"]["semantic_release"]
        assert configured["version_variables"] == ["main.py:__version__"]
        assert configured["branches"]["release"]["match"] == "trunk"


def test_ci_github_says_when_the_app_has_no_version_to_raise():
    runner = CliRunner()
    with isolated_filesystem() as directory:
        (Path(directory) / "app.py").write_text('app = App("x", "0.0.1")\n')
        result = runner.invoke(cli_app, ["plugin", "ci", "github"])
        assert result.exit_code == 0, result.output
        assert "has no __version__" in " ".join(result.output.split())


def test_ci_github_leaves_a_semantic_release_configuration_that_is_there():
    runner = CliRunner()
    with isolated_filesystem() as directory:
        mine = '[tool.semantic_release]\nversion_variables = ["mine.py:VERSION"]\n'
        (Path(directory) / "pyproject.toml").write_text(mine)
        result = runner.invoke(cli_app, ["plugin", "ci", "github"])
        assert result.exit_code == 0, result.output
        assert (Path(directory) / "pyproject.toml").read_text() == mine


def test_ci_gitlab_is_not_given_a_semantic_release_configuration():
    runner = CliRunner()
    with isolated_filesystem() as directory:
        result = runner.invoke(cli_app, ["plugin", "ci", "gitlab"])
        assert result.exit_code == 0, result.output
        assert not (Path(directory) / "pyproject.toml").exists()


@pytest.mark.skipif(sys.platform == "win32", reason="the action is a bash script, run on a Linux runner: Windows' `bash` is not one")
def test_the_action_releases_the_commit_the_job_tagged():
    """A push to a branch is a channel build, unless the job says it cut the release itself."""
    import yaml

    action = yaml.safe_load((Path(__file__).parents[2] / "ci" / "github" / "action.yml").read_text())
    assert action["inputs"]["release"]["default"] == "false"
    script = next(step["run"] for step in action["runs"]["steps"] if "run" in step)
    script = script.replace('$ARKITEKT plugin release "$TARGET" $ARGUMENTS', 'echo "channel=${ARKITEKT_CHANNEL:-}"')

    def channel(ref_type: str, release: str) -> str:
        env = {
            "PATH": os.environ["PATH"],
            "REPOSITORY": "ghcr.io/Me/App",
            "GITHUB_REF_TYPE": ref_type,
            "GITHUB_REF_NAME": "main",
            "RELEASE": release,
        }
        ran = subprocess.run(["bash", "-c", script], env=env, capture_output=True, text=True, check=True)
        return ran.stdout.strip()

    assert channel("branch", "false") == "channel=main"
    assert channel("branch", "") == "channel=main"
    assert channel("branch", "true") == "channel="
    assert channel("tag", "false") == "channel="


def test_the_shipped_action_runs_nothing_but_the_release_command():
    """A forge integration is a shell: the day it grows logic, the CLI has lost some."""
    import yaml

    action = yaml.safe_load((Path(__file__).parents[2] / "ci" / "github" / "action.yml").read_text())
    scripts = [step["run"] for step in action["runs"]["steps"] if "run" in step]
    assert len(scripts) == 1
    commands = [
        line.strip()
        for line in scripts[0].splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    assert commands[-1] == '$ARKITEKT plugin release "$TARGET" $ARGUMENTS'
    assert all(line.startswith(("export ", "if ")) for line in commands[:-1])
