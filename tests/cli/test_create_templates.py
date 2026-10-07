"""``arkitekt create``: what a template sets up, and that every part of it can be changed."""

import json
import shutil
import os
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from arkitekt.cli.main import cli_app

IDENTITY = ["--identifier", "com.test.app", "--author", "me", "--entrypoint", "app"]

needs_uv = pytest.mark.skipif(shutil.which("uv") is None, reason="uv is not installed")


def create(tmp_path: Path, *arguments: str, input: str | None = None):
    return CliRunner().invoke(cli_app, ["--work-dir", str(tmp_path), "create", *arguments], input=input)


@pytest.fixture
def fake_uv(monkeypatch):
    """Stand in for uv: a project appears without a network or a resolver."""
    real_run = subprocess.run

    def run(command, *args, **kwargs):
        if list(command[:2]) == ["uv", "init"]:
            Path(kwargs["cwd"], "pyproject.toml").write_text('[project]\nname = "x"\n')
            Path(kwargs["cwd"], ".python-version").write_text("3.12\n")
            return subprocess.CompletedProcess(command, 0)
        if list(command[:2]) == ["uv", "add"]:
            Path(kwargs["cwd"], "uv.lock").write_text("")
            return subprocess.CompletedProcess(command, 0)
        return real_run(command, *args, **kwargs)

    monkeypatch.setattr("shutil.which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr("subprocess.run", run)


def test_the_default_is_a_project_in_a_new_folder(tmp_path: Path, fake_uv):
    result = create(tmp_path, "my-app", *IDENTITY)
    assert result.exit_code == 0, result.output

    project = tmp_path / "my-app"
    assert (project / "app.py").exists()
    assert (project / "pyproject.toml").exists()

    # A flavour that installs from the project's lockfile...
    dockerfile = (project / ".arkitekt" / "flavours" / "vanilla" / "Dockerfile").read_text()
    assert "uv sync --frozen" in dockerfile
    assert "FROM python:3.12-slim" in dockerfile
    assert "ARG ARKITEKT_APP_VERSION" in dockerfile

    # ...and a workflow that has semantic-release cut the version, then calls the action.
    workflow = yaml.safe_load((project / ".github" / "workflows" / "release.yaml").read_text())
    steps = workflow["jobs"]["release"]["steps"]
    assert steps[-2]["run"].endswith("semantic-release version")
    assert steps[-1]["uses"].startswith("arkitektio/arkitekt/ci/github@")
    assert steps[-1]["with"]["release"] == "${{ steps.version.outputs.released }}"

    # semantic-release raises the version where the app declares it, and nowhere else.
    configured = tomllib.loads((project / "pyproject.toml").read_text())["tool"]
    assert configured["semantic_release"]["version_variables"] == ["app.py:__version__"]
    assert configured["pytest"]["ini_options"]["addopts"] == "-m 'not hub'"

    assert "cd my-app && arkitekt run dev" in result.output
    assert "semantic-release raises it for you" in " ".join(result.output.split())


def test_the_default_app_makes_a_random_image_and_blurs_one(tmp_path: Path, fake_uv):
    result = create(tmp_path, "my-app", *IDENTITY)
    assert result.exit_code == 0, result.output

    source = (tmp_path / "my-app" / "app.py").read_text()
    assert '__version__ = "0.0.1"' in source
    assert "App('com.test.app', __version__, author='me', scopes=['read'], services=[mikro_service])" in source
    assert "def generate_random_image(" in source and "def blur_image(" in source


def test_the_bare_template_keeps_the_starter_that_needs_no_service(tmp_path: Path):
    result = create(tmp_path, "--template", "bare", "--package-manager", "pip", *IDENTITY)
    assert result.exit_code == 0, result.output
    source = (tmp_path / "app.py").read_text()
    assert "def append_world(" in source and "mikro" not in source


def test_a_starter_can_be_named_for_either_template(tmp_path: Path, fake_uv):
    assert create(tmp_path, "one", "--starter", "filter", *IDENTITY).exit_code == 0
    assert "def moving_average(" in (tmp_path / "one" / "app.py").read_text()

    refused = create(tmp_path, "two", "--starter", "nope", *IDENTITY)
    assert refused.exit_code != 0
    assert not (tmp_path / "two" / "app.py").exists()


@pytest.mark.parametrize(
    ("extras", "installed"),
    [
        ([], "arkitekt[all]"),
        (["--with-extra", "rekuest"], "arkitekt[rekuest,mikro]"),
        (["--with-extra", "rekuest", "--with-extra", "mikro"], "arkitekt[rekuest,mikro]"),
        (["--with-extra", "rekuest", "--starter", "simple"], "arkitekt[rekuest]"),
        # `all` brings the clients, not the Qt integration.
        (["--template", "qt"], "arkitekt[all,qt]"),
        (["--template", "qt", "--with-extra", "rekuest"], "arkitekt[rekuest,qt]"),
        (["--template", "qt", "--with-extra", "rekuest", "--with-extra", "qt"], "arkitekt[rekuest,qt]"),
        (["--starter", "qt"], "arkitekt[all,qt]"),
        (["--template", "blok"], "arkitekt[all]"),
        (["--template", "blok", "--with-extra", "rekuest"], "arkitekt[rekuest,mikro]"),
    ],
)
def test_the_image_starter_brings_the_client_it_imports(tmp_path: Path, monkeypatch, extras, installed):
    commands = []

    def run(command, *args, **kwargs):
        commands.append(list(command))
        if command[1] == "init":
            Path(kwargs["cwd"], "pyproject.toml").write_text('[project]\nname = "x"\n')
        return subprocess.CompletedProcess(command, 0, stdout="")

    monkeypatch.setattr("shutil.which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr("subprocess.run", run)

    assert create(tmp_path, "my-app", *extras, *IDENTITY).exit_code == 0
    assert ["uv", "add", installed] in commands


def test_a_project_asks_for_its_name(tmp_path: Path, fake_uv, monkeypatch):
    monkeypatch.setattr("arkitekt.cli.commands.app.create.main.require_tty", lambda *a, **k: None)
    result = create(tmp_path, *IDENTITY, input="asked-app\n")
    assert result.exit_code == 0, result.output
    assert (tmp_path / "asked-app" / "app.py").exists()


def _answering(monkeypatch) -> None:
    """Let `create` ask its questions of the test's input."""
    monkeypatch.setattr("arkitekt.cli.commands.app.create.main.require_tty", lambda *a, **k: None)


@pytest.mark.parametrize(
    "answers",
    [
        "",  # left at the identifier
        "com.test.app\n",  # ...at the author
        "com.test.app\nme\n",  # ...at the app file
    ],
)
def test_a_wizard_that_is_left_halfway_makes_no_folder(tmp_path: Path, fake_uv, monkeypatch, answers: str):
    _answering(monkeypatch)
    result = create(tmp_path, "my-app", input=answers)
    assert result.exit_code != 0
    assert list(tmp_path.iterdir()) == []


def test_a_wizard_left_at_the_version_makes_no_folder(tmp_path: Path, fake_uv, monkeypatch):
    _answering(monkeypatch)
    result = create(tmp_path, "my-app", "--version", "not-a-version", *IDENTITY, input="")
    assert result.exit_code != 0
    assert list(tmp_path.iterdir()) == []


def test_the_folder_is_made_when_the_wizard_is_through(tmp_path: Path, fake_uv, monkeypatch):
    _answering(monkeypatch)
    result = create(tmp_path, "my-app", input="com.test.app\nme\napp\n")
    assert result.exit_code == 0, result.output
    assert (tmp_path / "my-app" / "app.py").exists()


@pytest.mark.parametrize(
    "options",
    [
        ["--version", "not-a-version", "--yes"],
        ["--package-manager", "pip", "--ci", "github", "--yes"],
        ["--no-flavour", "--ci", "github", "--yes"],
        ["--starter", "nope", "--yes"],
    ],
)
def test_a_project_that_is_refused_makes_no_folder(tmp_path: Path, fake_uv, options: list[str]):
    result = create(tmp_path, "my-app", *options)
    assert result.exit_code != 0
    assert list(tmp_path.iterdir()) == []


def test_without_uv_a_uv_project_is_refused_before_its_folder_is_made(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("shutil.which", lambda name: None)
    result = create(tmp_path, "my-app", "--package-manager", "uv", *IDENTITY)
    assert result.exit_code != 0
    assert "uv is not installed" in result.output
    assert list(tmp_path.iterdir()) == []


def test_an_app_file_that_is_kept_is_asked_about_before_anything_is_made(tmp_path: Path, fake_uv, monkeypatch):
    _answering(monkeypatch)
    (tmp_path / "app.py").write_text("mine\n")
    result = create(tmp_path, ".", *IDENTITY, input="n\n")
    assert result.exit_code == 0, result.output
    assert (tmp_path / "app.py").read_text() == "mine\n"

    overwritten = create(tmp_path, ".", *IDENTITY, input="y\n")
    assert overwritten.exit_code == 0, overwritten.output
    assert "generate_random_image" in (tmp_path / "app.py").read_text()


def test_a_project_without_a_name_cannot_be_assumed(tmp_path: Path, fake_uv):
    result = create(tmp_path, "--yes")
    assert result.exit_code == 1
    assert "arkitekt create my-app" in result.output
    assert list(tmp_path.iterdir()) == []


def test_a_project_can_be_created_in_this_folder(tmp_path: Path, fake_uv):
    result = create(tmp_path, ".", "--yes")
    assert result.exit_code == 0, result.output
    assert (tmp_path / "app.py").exists()
    assert (tmp_path / ".github" / "workflows" / "release.yaml").exists()


def test_the_bare_template_writes_only_the_app_file(tmp_path: Path):
    result = create(tmp_path, "--template", "bare", "--package-manager", "pip", *IDENTITY)
    assert result.exit_code == 0, result.output
    assert sorted(p.name for p in tmp_path.iterdir()) == ["app.py"]


@pytest.mark.parametrize(
    ("options", "flavour", "github", "gitlab"),
    [
        (["--ci", "none"], True, False, False),
        (["--ci", "gitlab"], True, False, True),
        (["--no-flavour"], False, False, False),
        (["--template", "bare", "--package-manager", "uv", "--flavour", "--ci", "github"], True, True, False),
    ],
)
def test_every_part_of_a_template_has_its_own_option(
    tmp_path: Path, fake_uv, options: list[str], flavour: bool, github: bool, gitlab: bool
):
    result = create(tmp_path, ".", *options, *IDENTITY)
    assert result.exit_code == 0, result.output
    assert (tmp_path / ".arkitekt" / "flavours" / "vanilla").exists() is flavour
    assert (tmp_path / ".github" / "workflows" / "release.yaml").exists() is github
    assert (tmp_path / ".gitlab-ci.yml").exists() is gitlab


def test_a_project_on_pip_gets_the_pip_image_and_no_workflow(tmp_path: Path):
    result = create(tmp_path, "my-app", "--package-manager", "pip", *IDENTITY)
    assert result.exit_code == 0, result.output
    project = tmp_path / "my-app"
    assert "pip install" in (project / ".arkitekt" / "flavours" / "vanilla" / "Dockerfile").read_text()
    assert not (project / ".github").exists()


def test_without_uv_a_project_falls_back_to_a_plain_app(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("shutil.which", lambda name: None)
    result = create(tmp_path, "my-app", *IDENTITY)
    assert result.exit_code == 0, result.output
    assert "uv is not installed" in result.output
    assert (tmp_path / "my-app" / "app.py").exists()
    assert not (tmp_path / "my-app" / "pyproject.toml").exists()


@pytest.mark.parametrize(
    ("options", "message"),
    [
        (["--package-manager", "pip", "--ci", "github"], "needs a uv project"),
        (["--no-flavour", "--ci", "github"], "nothing to release"),
        (["--template", "nope"], "is not one of project, blok, qt, bare."),
    ],
)
def test_parts_that_cannot_go_together_are_refused(tmp_path: Path, fake_uv, options: list[str], message: str):
    result = create(tmp_path, "my-app", *options, *IDENTITY)
    assert result.exit_code != 0
    # The message is boxed, and wrapped where the box ends.
    assert message in " ".join(result.output.replace("│", " ").split())


def test_an_existing_workflow_is_left_alone(tmp_path: Path, fake_uv):
    workflow = tmp_path / ".github" / "workflows" / "release.yaml"
    workflow.parent.mkdir(parents=True)
    workflow.write_text("mine\n")
    result = create(tmp_path, ".", "--yes")
    assert result.exit_code == 0, result.output
    assert workflow.read_text() == "mine\n"


@needs_uv
@pytest.mark.needs_docker  # not docker itself: the same machines that have a network
def test_a_real_project_is_one_its_own_workflow_can_release(tmp_path: Path, monkeypatch):
    """With the real uv: the project resolves, and git is on `main` whatever git starts on."""
    gitconfig = tmp_path / "gitconfig"
    gitconfig.write_text("[init]\n\tdefaultBranch = master\n")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(gitconfig))
    result = create(tmp_path, "real-app", "--with-extra", "rekuest", *IDENTITY)
    assert result.exit_code == 0, result.output
    project = tmp_path / "real-app"
    assert (project / "uv.lock").exists()
    branch = subprocess.run(
        ["git", "symbolic-ref", "--short", "HEAD"], cwd=project, stdout=subprocess.PIPE, text=True
    ).stdout.strip()
    workflow = yaml.safe_load((project / ".github" / "workflows" / "release.yaml").read_text())
    assert branch == "main"
    assert workflow[True]["push"]["branches"] == ["main"]


# ---------------------------------------------------------------------------
# The blok template
# ---------------------------------------------------------------------------


def test_the_blok_template_is_a_whole_project_around_a_blok_agent(tmp_path: Path, fake_uv):
    result = create(tmp_path, "analyst", "--template", "blok", *IDENTITY)
    assert result.exit_code == 0, result.output

    project = tmp_path / "analyst"
    # Every part the default project has.
    assert (project / ".arkitekt" / "flavours" / "vanilla" / "Dockerfile").exists()
    assert (project / ".github" / "workflows" / "release.yaml").exists()
    configured = tomllib.loads((project / "pyproject.toml").read_text())["tool"]
    assert configured["semantic_release"]["version_variables"] == ["app.py:__version__"]
    assert sorted(p.name for p in (project / "tests").glob("*.py")) == ["conftest.py", "test_app.py", "test_app_hub.py"]

    source = (project / "app.py").read_text()
    assert '__version__ = "0.0.1"' in source
    assert "App('com.test.app', __version__, author='me', scopes=['read'], services=[mikro_service])" in source
    assert "@app.state" in source and 'app.blok(\n    "analysis",' in source
    output = " ".join(result.output.split())
    assert f"{HUB_TEST} tests it against a hub" in output
    assert "cd analyst && arkitekt run dev" in output


def test_a_blok_agent_declares_its_panel_its_state_and_its_actions(tmp_path: Path, fake_uv):
    """What a deployment is told of the app: read off the declaration, as `inspect all` prints it."""
    pytest.importorskip("mikro")
    assert create(tmp_path, "analyst", "-t", "blok", *IDENTITY).exit_code == 0

    result = CliRunner().invoke(cli_app, ["--work-dir", str(tmp_path / "analyst"), "inspect", "all", "-mr"])
    assert result.exit_code == 0, result.output
    declared = json.loads(result.output.split("--START_AGENT--")[1].split("--END_AGENT--")[0])

    assert [blok["key"] for blok in declared["bloks"]] == ["analysis"]
    assert "Analysis" in json.dumps(declared["states"])
    interfaces = json.dumps(declared["implementations"])
    for action in ("generate_test_image", "analyse_image", "segment_image", "clear_history"):
        assert action in interfaces


def test_a_panel_that_names_what_the_app_does_not_have_fails_its_tests(tmp_path: Path, fake_uv):
    """The project's own tests are what catches a typo in the panel, before a deployment does."""
    pytest.importorskip("mikro")
    assert create(tmp_path, "analyst", "-t", "blok", *IDENTITY).exit_code == 0
    project = tmp_path / "analyst"
    app_file = project / "app.py"
    app_file.write_text(app_file.read_text().replace("@self.Analysis.status", "@self.Analysis.statuz"))

    ran = _pytest_in(project, "-q", "-k", "panel_is_declared")

    assert ran.returncode != 0
    assert "statuz" in ran.stdout + ran.stderr


# ---------------------------------------------------------------------------
# The qt template
# ---------------------------------------------------------------------------


def _has_qt_binding() -> bool:
    try:
        from qtpy import QtWidgets  # noqa: F401
    except Exception:
        return False
    return True


def test_the_qt_template_is_a_project_without_an_image(tmp_path: Path, fake_uv):
    result = create(tmp_path, "viewer", "--template", "qt", *IDENTITY)
    assert result.exit_code == 0, result.output

    project = tmp_path / "viewer"
    assert sorted(p.name for p in project.iterdir()) == [".python-version", "app.py", "pyproject.toml", "tests", "uv.lock"]
    assert sorted(p.name for p in (project / "tests").glob("*.py")) == ["conftest.py", "test_app.py"]
    assert "semantic_release" not in (project / "pyproject.toml").read_text()

    source = (project / "app.py").read_text()
    compile(source, "app.py", "exec")
    assert '__version__ = "0.0.1"' in source
    # The window is the app's context: an action asks for it by its class.
    assert "app = QtApp('com.test.app', __version__, author='me', scopes=['read'], app_context=Window)" in source
    assert "MagicBar(self.runtime, context=self)" in source
    assert "def show_message(text: str, window: Window) -> str:" in source
    assert "app_context=Window" in source


def test_the_qt_template_says_what_is_left_to_do(tmp_path: Path, fake_uv):
    output = " ".join(create(tmp_path, "viewer", "-t", "qt", *IDENTITY).output.split())
    assert "A Qt app needs a Qt binding" in output and "uv add pyqt6" in output
    assert "cd viewer && uv run python app.py" in output
    assert "arkitekt run dev" not in output
    assert "releases it" not in output


def test_a_qt_app_on_pip_is_started_and_completed_with_pip(tmp_path: Path):
    output = " ".join(
        create(tmp_path, "viewer", "-t", "qt", "--package-manager", "pip", "--entrypoint", "main", "--identifier", "x", "--author", "me").output.split()
    )
    assert "pip install pyqt6" in output
    assert "cd viewer && python main.py" in output


def test_a_qt_project_can_still_be_given_an_image_and_a_workflow(tmp_path: Path, fake_uv):
    refused = create(tmp_path, "one", "-t", "qt", "--ci", "github", *IDENTITY)
    assert refused.exit_code != 0 and "nothing to release" in refused.output
    assert not (tmp_path / "one").exists()

    result = create(tmp_path, "two", "-t", "qt", "--flavour", "--ci", "github", *IDENTITY)
    assert result.exit_code == 0, result.output
    assert (tmp_path / "two" / ".arkitekt" / "flavours" / "vanilla").exists()
    assert (tmp_path / "two" / ".github" / "workflows" / "release.yaml").exists()


def test_the_templates_are_all_in_the_help():
    output = " ".join(CliRunner().invoke(cli_app, ["create", "--help"], terminal_width=200).output.split())
    for name in ("'project':", "'blok':", "'qt':", "'bare':"):
        assert name in output


@pytest.mark.skipif(_has_qt_binding(), reason="a Qt binding is installed")
def test_without_a_binding_the_qt_tests_are_skipped_and_say_why(tmp_path: Path, fake_uv):
    assert create(tmp_path, "viewer", "-t", "qt", *IDENTITY).exit_code == 0

    ran = _pytest_in(tmp_path / "viewer", "-q", "-rs")

    assert ran.returncode in (0, 5), ran.stdout + ran.stderr  # 5: nothing but skips was collected
    assert "1 skipped" in ran.stdout
    assert "No Qt binding is installed: `uv add pyqt6`" in ran.stdout


@pytest.mark.skipif(not _has_qt_binding(), reason="no Qt binding is installed")
@pytest.mark.parametrize("entrypoint", ["app", "main"])
def test_with_a_binding_the_qt_tests_pass_without_a_screen(tmp_path: Path, fake_uv, entrypoint: str):
    result = create(tmp_path, "viewer", "-t", "qt", "--identifier", "com.test.app", "--author", "me", "--entrypoint", entrypoint)
    assert result.exit_code == 0, result.output

    ran = _pytest_in(tmp_path / "viewer", "-q")

    assert ran.returncode == 0, ran.stdout + ran.stderr
    assert "6 passed" in ran.stdout


def _git(project: Path, *arguments: str) -> str:
    identity = ["-c", "user.name=tester", "-c", "user.email=tester@example.com"]
    return subprocess.run(
        ["git", *identity, *arguments], cwd=project, check=True, stdout=subprocess.PIPE, text=True
    ).stdout.strip()


def _semantic_release(project: Path, output: Path) -> None:
    """What the workflow's `Version` step runs, kept from pushing: there is nowhere to push to."""
    env = {
        **os.environ,
        "GITHUB_ACTIONS": "true",
        "GITHUB_OUTPUT": str(output),
        **{f"GIT_{who}_{what}": value for who in ("AUTHOR", "COMMITTER") for what, value in (("NAME", "t"), ("EMAIL", "t@example.com"))},
    }
    env.pop("GH_TOKEN", None)
    ran = subprocess.run(
        [sys.executable, "-m", "semantic_release", "version", "--no-push", "--no-vcs-release"],
        cwd=project,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert ran.returncode == 0, ran.stdout + ran.stderr


@pytest.mark.parametrize("entrypoint", ["app", "main"])
def test_what_semantic_release_tags_is_a_release_the_app_declares(tmp_path: Path, fake_uv, entrypoint: str):
    """The whole loop of the workflow, locally: a `feat:` raises the version in the app
    file, and the commit it tags is one `plugin release` takes for that release."""
    pytest.importorskip("semantic_release")
    from arkitekt.cli.commands.plugin.release import resolve

    result = create(tmp_path, "released", "--starter", "simple", "--identifier", "com.test.app", "--author", "me", "--entrypoint", entrypoint)
    assert result.exit_code == 0, result.output
    project = tmp_path / "released"
    (project / ".gitignore").write_text("__pycache__/\n")
    _git(project, "init", "-q", "-b", "main")
    _git(project, "remote", "add", "origin", "https://github.com/example/released.git")
    _git(project, "add", "-A")
    _git(project, "commit", "-q", "-m", "feat: the app")
    output = tmp_path / "output"

    # Before: a build of the branch.
    assert resolve("0.0.1", str(project)).channel == "main"

    _semantic_release(project, output)

    outputs = dict(line.split("=", 1) for line in output.read_text().splitlines() if "=" in line)
    assert (outputs["released"], outputs["version"], outputs["tag"]) == ("true", "0.1.0", "v0.1.0")
    assert f'__version__ = "0.1.0"' in (project / f"{entrypoint}.py").read_text()
    assert _git(project, "tag", "--points-at", "HEAD") == "v0.1.0"
    # Nothing left over: a release is not made from a tree that changed.
    assert _git(project, "status", "--porcelain") == ""
    released = resolve("0.1.0", str(project))
    assert (released.version, released.channel) == ("0.1.0", None)

    # A push that says nothing of a version cuts none, and is a build of the branch again.
    _git(project, "commit", "-q", "--allow-empty", "-m", "docs: a word")
    output.write_text("")
    _semantic_release(project, output)
    assert "released=false" in output.read_text()
    assert resolve("0.1.0", str(project)).channel == "main"


# ---------------------------------------------------------------------------
# The first test
# ---------------------------------------------------------------------------


def _run_the_projects_tests(project: Path) -> subprocess.CompletedProcess[str]:
    """Run a created project's tests with this interpreter: its own environment is uv's to make."""
    env = {**os.environ, "PYTHONPATH": os.pathsep.join(p for p in sys.path if p)}
    env.pop("ARKITEKT_APP", None)
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"],
        cwd=project,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.parametrize(("starter", "passing"), [("image", 7), ("blok", 15), ("simple", 2), ("filter", 3)])
def test_a_project_comes_with_tests_that_pass_offline(tmp_path: Path, fake_uv, starter: str, passing: int):
    if starter in ("image", "blok"):
        pytest.importorskip("mikro")
    result = create(tmp_path, "tested", "--starter", starter, *IDENTITY)
    assert result.exit_code == 0, result.output
    project = tmp_path / "tested"
    assert (project / "tests" / "conftest.py").exists()
    assert "uv run pytest" in result.output

    ran = _run_the_projects_tests(project)

    assert ran.returncode == 0, ran.stdout + ran.stderr
    assert f"{passing} passed" in ran.stdout


# ---------------------------------------------------------------------------
# The conftest a project is given
# ---------------------------------------------------------------------------


def _pytest_in(project: Path, *arguments: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    """Run pytest on a created project the way `uv run pytest` does: as the script, not `python -m`.

    The difference is the one the conftest is there for: `python -m pytest` puts the
    folder it runs in on the path, and the script does not.
    """
    env = {**os.environ, "PYTHONPATH": os.pathsep.join(p for p in sys.path if p and Path(p) != project)}
    env.pop("ARKITEKT_APP", None)
    script = "import sys, pytest; sys.path[:] = [p for p in sys.path if p]; sys.exit(pytest.main(sys.argv[1:]))"
    return subprocess.run(
        [sys.executable, "-c", script, "-p", "no:cacheprovider", *arguments],
        cwd=cwd or project,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.fixture
def image_project(tmp_path: Path, fake_uv) -> Path:
    pytest.importorskip("mikro")
    assert create(tmp_path, "tested", *IDENTITY).exit_code == 0
    return tmp_path / "tested"


def test_a_project_has_one_test_file_with_no_server_and_one_against_a_hub(image_project: Path, tmp_path: Path):
    tests = image_project / "tests"
    assert sorted(p.name for p in tests.glob("*.py")) == ["conftest.py", "test_app.py", "test_app_hub.py"]

    offline, hub = (tests / "test_app.py").read_text(), (tests / "test_app_hub.py").read_text()
    # Nothing of a hub in the one, and nothing but a hub in the other.
    assert "teststack" not in offline and "pytest.mark.hub" not in offline
    assert "pytestmark = pytest.mark.hub" in hub
    # Each names the other, by the name it was written under.
    assert "test_app_hub.py" in offline and "test_app.py" in hub
    assert "__ENTRYPOINT__" not in offline + hub

    # Each file is one suite: the first all runs, the second is all the hub's.
    first = _pytest_in(image_project, "-q", "tests/test_app.py")
    assert "7 passed" in first.stdout and "deselected" not in first.stdout
    second = _pytest_in(image_project, "-q", "-m", "hub", "--collect-only", "tests/test_app_hub.py")
    assert "2 tests collected" in second.stdout, second.stdout
    assert "2 deselected" in _pytest_in(image_project, "-q", "tests/test_app_hub.py").stdout


# A created file is named the way the platform names it: `tests\test_app.py` on Windows.
APP_TEST = str(Path("tests") / "test_app.py")
HUB_TEST = str(Path("tests") / "test_app_hub.py")


def test_create_says_how_to_run_each_of_them(tmp_path: Path, fake_uv):
    output = " ".join(create(tmp_path, "tested", *IDENTITY).output.split())
    assert f"{APP_TEST} tests it" in output and "uv run pytest`" in output
    assert f"{HUB_TEST} tests it against a hub" in output and "uv run pytest -m hub" in output


@pytest.mark.parametrize("starter", ["simple", "filter"])
def test_a_starter_without_a_service_has_no_hub_tests(tmp_path: Path, fake_uv, starter: str):
    result = create(tmp_path, "tested", "--starter", starter, *IDENTITY)
    assert result.exit_code == 0, result.output
    assert sorted(p.name for p in (tmp_path / "tested" / "tests").glob("*.py")) == ["conftest.py", "test_app.py"]
    assert "against a hub" not in result.output


def test_the_conftest_is_what_lets_a_test_import_the_app(image_project: Path):
    """Without the project on the path `from app import ...` fails; the conftest puts it there."""
    ran = _pytest_in(image_project, "-q")
    assert ran.returncode == 0, ran.stdout + ran.stderr
    assert "7 passed" in ran.stdout

    conftest = image_project / "tests" / "conftest.py"
    conftest.write_text("\n".join(line for line in conftest.read_text().splitlines() if "sys.path" not in line))
    without = _pytest_in(image_project, "-q")
    assert without.returncode != 0
    assert "No module named 'app'" in without.stdout + without.stderr


def test_the_projects_tests_run_from_any_folder(image_project: Path, tmp_path: Path):
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    ran = _pytest_in(image_project, "-q", "--rootdir", str(image_project), str(image_project), cwd=elsewhere)
    assert ran.returncode == 0, ran.stdout + ran.stderr
    assert "7 passed" in ran.stdout


def test_the_conftest_loads_every_fixture_the_tests_ask_for(image_project: Path):
    ran = _pytest_in(image_project, "--fixtures", "-q")
    assert ran.returncode == 0, ran.stdout + ran.stderr
    for fixture in ("call", "local_runtime", "arkitekt_app", "arkitekt_clients", "teststack", "hub_call"):
        assert f"\n{fixture} " in ran.stdout, fixture
    assert "hub: end to end" in _pytest_in(image_project, "--markers").stdout


def test_a_bare_pytest_leaves_the_hub_tests_out_and_m_hub_selects_them(image_project: Path):
    # `fake_uv` writes a pyproject without a build of its own: pytest reads it all the same.
    assert "2 deselected" in _pytest_in(image_project, "-q").stdout

    collected = _pytest_in(image_project, "-q", "-m", "hub", "--collect-only")
    assert collected.returncode == 0, collected.stdout + collected.stderr
    assert "test_a_random_image_is_stored" in collected.stdout
    assert "test_a_blurred_image_is_as_large_and_smoother" in collected.stdout
    assert "7 deselected" in collected.stdout


def test_the_hub_tests_are_skipped_not_failed_where_no_hub_can_be_made(image_project: Path, tmp_path: Path):
    """konstruktor is hidden from the run, so this holds wherever the suite runs.

    Where it is installed it also announces a pytest plugin, which pytest would load
    before any test could say it is missing: so that is switched off for the run, as it
    is where the package is not there at all.
    """
    hidden = tmp_path / "hidden"
    (hidden / "konstruktor").mkdir(parents=True)
    (hidden / "konstruktor" / "__init__.py").write_text("raise ImportError('hidden for the test')\n")
    (hidden / "sitecustomize.py").write_text("")
    env_path = os.pathsep.join([str(hidden), *(p for p in sys.path if p)])
    ran = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-rs", "-p", "no:cacheprovider", "-p", "no:konstruktor", "-m", "hub"],
        cwd=image_project,
        env={**os.environ, "PYTHONPATH": env_path},
        capture_output=True,
        text=True,
        check=False,
    )
    assert ran.returncode == 0, ran.stdout + ran.stderr
    assert "2 skipped" in ran.stdout
    assert "konstruktor, which is not installed" in ran.stdout


def test_the_tests_of_an_app_in_another_file_import_that_file(tmp_path: Path, fake_uv):
    pytest.importorskip("mikro")
    assert create(tmp_path, "tested", "--identifier", "com.test.app", "--author", "me", "--entrypoint", "main").exit_code == 0
    project = tmp_path / "tested"
    assert "from main import app, blur_pixels, random_pixels" in (project / "tests" / "test_main.py").read_text()
    assert (project / "tests" / "test_main_hub.py").exists()
    assert 'os.environ.setdefault("ARKITEKT_APP", "main")' in (project / "tests" / "conftest.py").read_text()

    ran = _pytest_in(project, "-q")

    assert ran.returncode == 0, ran.stdout + ran.stderr
    assert "7 passed" in ran.stdout


def test_pytest_options_that_are_there_are_left_alone(tmp_path: Path):
    from arkitekt.cli.commands.app.create.main import write_pytest_options

    assert write_pytest_options(str(tmp_path)) is False  # no pyproject: nothing to write to
    mine = '[tool.pytest.ini_options]\naddopts = "-x"\n'
    (tmp_path / "pyproject.toml").write_text(mine)
    assert write_pytest_options(str(tmp_path)) is False
    assert (tmp_path / "pyproject.toml").read_text() == mine


def test_the_tests_find_an_app_that_is_not_in_app_py(tmp_path: Path, fake_uv):
    result = create(tmp_path, "tested", "--identifier", "com.test.app", "--author", "me", "--entrypoint", "main")
    assert result.exit_code == 0, result.output
    project = tmp_path / "tested"
    assert (project / "tests" / "test_main.py").exists()

    ran = _run_the_projects_tests(project)

    assert ran.returncode == 0, ran.stdout + ran.stderr


def test_pytest_becomes_a_dev_dependency_of_a_uv_project(tmp_path: Path, monkeypatch):
    commands = []
    real_run = subprocess.run

    def run(command, *args, **kwargs):
        if command[0] == "uv":
            commands.append(list(command))
            if command[1] == "init":
                Path(kwargs["cwd"], "pyproject.toml").write_text('[project]\nname = "x"\n')
            return subprocess.CompletedProcess(command, 0)
        return real_run(command, *args, **kwargs)

    monkeypatch.setattr("shutil.which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr("subprocess.run", run)

    assert create(tmp_path, "tested", *IDENTITY).exit_code == 0
    assert ["uv", "add", "--dev", "pytest"] in commands


@pytest.mark.parametrize("options", [["--no-tests"], ["--template", "bare"]])
def test_tests_are_a_part_like_the_others(tmp_path: Path, fake_uv, options: list[str]):
    result = create(tmp_path, ".", *options, *IDENTITY)
    assert result.exit_code == 0, result.output
    assert not (tmp_path / "tests").exists()


def test_tests_that_are_there_are_left_alone(tmp_path: Path, fake_uv):
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_mine.py").write_text("def test_mine():\n    pass\n")

    result = create(tmp_path, ".", *IDENTITY)

    assert result.exit_code == 0, result.output
    assert sorted(p.name for p in (tmp_path / "tests").iterdir()) == ["test_mine.py"]
    assert "left as it is" in result.output
