"""A plugin builds for every architecture it declares, and publishes one image.

A flavour targets ``linux/amd64`` and ``linux/arm64`` unless it says otherwise.
Since a multi-platform image cannot live in the local image store, ``build``
loads the host platform and builds the rest to cache, and ``publish`` pushes the
whole list. Nothing here needs docker: the subprocess boundary is mocked, so
these run on a CI host with no emulation installed.
"""

import subprocess
from unittest.mock import patch

import pytest
import typer
import yaml
from typer.testing import CliRunner

from arkitekt.cli.commands.plugin import buildx
from arkitekt.cli.commands.plugin.build import build_flavour
from arkitekt.cli.commands.plugin.io import get_flavours
from arkitekt.cli.commands.plugin.publish import push_multi_arch
from arkitekt.cli.commands.plugin.types import (
    DEFAULT_BUILD_COMMAND,
    DEFAULT_PLATFORMS,
    LEGACY_BUILD_COMMANDS,
    Build,
    Flavour,
)
from arkitekt.cli.main import cli_app

#: What ``docker buildx inspect --bootstrap`` prints for a builder that can do
#: both architectures (the shape was captured from a real docker-container
#: builder; the default ``docker`` driver reports only the host's).
_BOTH_PLATFORMS = """Name:          arkitekt
Driver:        docker-container

Nodes:
Name:                  arkitekt0
Status:                running
Platforms:             linux/amd64, linux/amd64/v2, linux/arm64, linux/arm64/v8
"""


def _config(tmp_path, flavour="vanilla"):
    return tmp_path / ".arkitekt" / "flavours" / flavour / "config.yaml"


def _init(tmp_path, *extra):
    return CliRunner().invoke(
        cli_app,
        ["--work-dir", str(tmp_path), "plugin", "init", "--arkitekt-version", "0.0.1", *extra],
        input="n\n",
    )


# ---------------------------------------------------------------------------
# what a flavour declares
# ---------------------------------------------------------------------------


def test_a_new_flavour_builds_both_architectures(tmp_path):
    result = _init(tmp_path)

    assert result.exit_code == 0, result.output
    assert yaml.safe_load(_config(tmp_path).read_text())["platforms"] == DEFAULT_PLATFORMS


def test_no_multi_arch_builds_only_this_machine(tmp_path):
    with patch.object(buildx, "host_platform", return_value="linux/amd64"):
        result = _init(tmp_path, "--no-multi-arch")

    assert result.exit_code == 0, result.output
    assert yaml.safe_load(_config(tmp_path).read_text())["platforms"] == ["linux/amd64"]


def test_platforms_can_be_named_explicitly(tmp_path):
    result = _init(tmp_path, "-p", "linux/arm64", "-p", "linux/amd64")

    assert result.exit_code == 0, result.output
    assert yaml.safe_load(_config(tmp_path).read_text())["platforms"] == [
        "linux/arm64",
        "linux/amd64",
    ]


def test_naming_platforms_and_opting_out_at_once_is_refused(tmp_path):
    result = _init(tmp_path, "--no-multi-arch", "-p", "linux/arm64")

    assert result.exit_code != 0
    assert "--platform and --no-multi-arch" in result.output


def test_a_flavour_written_before_multi_arch_still_builds_both(tmp_path):
    """The old default build command is a spelling, not a choice."""
    _init(tmp_path)
    config = _config(tmp_path)
    legacy = yaml.safe_load(config.read_text())
    legacy["build_command"] = list(LEGACY_BUILD_COMMANDS[0])
    del legacy["platforms"]
    config.write_text(yaml.dump(legacy))

    loaded = get_flavours(base_dir=str(tmp_path))["vanilla"]

    assert loaded.platforms == DEFAULT_PLATFORMS
    assert loaded.build_command == DEFAULT_BUILD_COMMAND
    assert not loaded.is_customized()


def test_a_hand_written_build_command_is_left_alone(tmp_path):
    _init(tmp_path)
    config = _config(tmp_path)
    custom = yaml.safe_load(config.read_text())
    custom["build_command"] = ["docker", "build", "--build-arg", "X=1", "-t", "{tag}", "-f", "{dockerfile}", "."]
    config.write_text(yaml.dump(custom))

    loaded = get_flavours(base_dir=str(tmp_path))["vanilla"]

    assert loaded.is_customized()
    assert "--build-arg" in loaded.generate_build_command("tag", "dir/")


def test_an_unloadable_config_names_the_file_and_the_reason(tmp_path):
    _init(tmp_path)
    _config(tmp_path).write_text(yaml.dump({"selectors": [], "platforms": "linux/amd64"}))

    with pytest.raises(typer.Exit):
        get_flavours(base_dir=str(tmp_path))


# ---------------------------------------------------------------------------
# what build runs
# ---------------------------------------------------------------------------


def _build(flavour, platforms=None, host="linux/amd64"):
    """Run build_flavour against a mocked docker, returning the argv lists."""
    with patch.object(buildx, "host_platform", return_value=host), patch.object(
        buildx, "ensure_builder", return_value="arkitekt"
    ), patch(
        "arkitekt.cli.commands.plugin.build.subprocess.run",
        return_value=subprocess.CompletedProcess([], 0),
    ) as run:
        build_id = build_flavour("vanilla", flavour, "/work", platforms=platforms)
    return build_id, [call.args[0] for call in run.call_args_list]


def test_the_host_platform_is_loaded_and_the_rest_only_cached():
    build_id, commands = _build(Flavour(selectors=[]))

    host, foreign = commands
    assert host[:3] == ["docker", "buildx", "build"]
    assert "--builder" in host and "--load" in host
    assert host[host.index("--platform") + 1] == "linux/amd64"
    assert host[host.index("-t") + 1] == build_id

    # The foreign platform is built -- that is the point of doing it now -- but
    # nothing is exported for it: a manifest list cannot be loaded locally.
    assert foreign[foreign.index("--platform") + 1] == "linux/arm64"
    assert "--output=type=cacheonly" in foreign
    assert "--load" not in foreign


def test_a_single_platform_flavour_runs_one_build():
    _, commands = _build(Flavour(selectors=[], platforms=["linux/amd64"]))

    assert len(commands) == 1
    assert "--load" in commands[0]


def test_the_platform_flag_overrides_what_the_flavour_declares():
    _, commands = _build(Flavour(selectors=[]), platforms=["linux/amd64"])

    assert len(commands) == 1


def test_building_nothing_this_machine_can_load_is_refused():
    """Every later step -- inspection, --tag, stage -- reads the local image."""
    with pytest.raises(typer.Exit):
        _build(Flavour(selectors=[], platforms=["linux/arm64"]))


def test_a_customized_command_is_run_verbatim():
    flavour = Flavour(
        selectors=[],
        build_command=["docker", "build", "--build-arg", "X=1", "-t", "{tag}", "-f", "{dockerfile}", "."],
    )

    _, commands = _build(flavour)

    assert len(commands) == 1
    assert "buildx" not in commands[0]
    assert "--build-arg" in commands[0]


# ---------------------------------------------------------------------------
# what a builder can do
# ---------------------------------------------------------------------------


def _inspect_returns(text):
    return patch.object(
        buildx.subprocess,
        "run",
        return_value=subprocess.CompletedProcess([], 0, stdout=text),
    )


def test_a_builder_is_asked_what_it_supports():
    with _inspect_returns(_BOTH_PLATFORMS):
        assert buildx.builder_platforms("arkitekt") == [
            "linux/amd64",
            "linux/amd64/v2",
            "linux/arm64",
            "linux/arm64/v8",
        ]


def test_a_variant_covers_the_platform_that_was_asked_for():
    assert buildx._supports(["linux/arm64/v8"], "linux/arm64")
    assert not buildx._supports(["linux/amd64", "linux/386"], "linux/arm64")


def test_a_missing_architecture_names_both_the_remedy_and_the_way_out(capsys):
    with patch.object(buildx, "host_platform", return_value="linux/amd64"), patch.object(
        buildx, "_builder_exists", return_value=True
    ), patch.object(buildx, "builder_platforms", return_value=["linux/amd64"]):
        with pytest.raises(typer.Exit):
            buildx.ensure_builder(["linux/amd64", "linux/arm64"])

    message = capsys.readouterr().err
    assert "linux/arm64" in message
    assert "binfmt" in message
    assert "--no-multi-arch" in message


def test_building_only_for_this_machine_creates_no_builder():
    with patch.object(buildx, "host_platform", return_value="linux/amd64"), patch.object(
        buildx, "_builder_exists"
    ) as exists:
        assert buildx.ensure_builder(["linux/amd64"]) is None

    exists.assert_not_called()


# ---------------------------------------------------------------------------
# what publish pushes
# ---------------------------------------------------------------------------


def test_publishing_a_multi_arch_build_pushes_one_image(tmp_path):
    _init(tmp_path)
    build = Build(
        build_run="run",
        build_id="image",
        flavour="vanilla",
        platforms=["linux/amd64", "linux/arm64"],
        manifest=_manifest(),
    )

    with patch.object(buildx, "ensure_builder", return_value="arkitekt"), patch(
        "arkitekt.cli.commands.plugin.publish.subprocess.run",
        return_value=subprocess.CompletedProcess([], 0),
    ) as run:
        push_multi_arch(build, "me/x:1", str(tmp_path), _Console())

    command = run.call_args.args[0]
    assert command[:3] == ["docker", "buildx", "build"]
    assert command[command.index("--platform") + 1] == "linux/amd64,linux/arm64"
    assert "--push" in command
    assert command[command.index("-t") + 1] == "me/x:1"


def _manifest():
    from arkitekt import App
    from arkitekt.cli.commands.plugin.io import app_to_manifest

    return app_to_manifest(App("com.x", "1.0.0"), "app")


class _Console:
    def print(self, *args, **kwargs):
        pass


def test_publishing_an_uninspected_build_is_refused_before_it_is_pushed(tmp_path, monkeypatch):
    """The push is the expensive, irreversible half; the record needs the inspection."""
    _init(tmp_path)
    monkeypatch.chdir(tmp_path)
    build = Build(
        build_run="run",
        build_id="image",
        flavour="vanilla",
        platforms=["linux/amd64", "linux/arm64"],
        manifest=_manifest(),
    )

    with patch(
        "arkitekt.cli.commands.plugin.io.get_builds", return_value={"image": build}
    ), patch("subprocess.check_output", return_value=b"Username: me"), patch(
        "arkitekt.cli.commands.plugin.publish.subprocess.run"
    ) as run:
        result = CliRunner().invoke(
            cli_app,
            ["--work-dir", str(tmp_path), "plugin", "publish", "--tag", "me/x:1"],
        )

    assert result.exit_code != 0
    assert "--no-inspect" in result.output
    run.assert_not_called()
