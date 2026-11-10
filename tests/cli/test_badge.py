"""``arkitekt plugin badge``: the README badge that installs the app's package."""

import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from arkitekt.cli.commands.plugin.badge import (
    END,
    PLACEHOLDER,
    START,
    install_badge,
    install_path,
    normalize_reference,
    package_for_remote,
    write_badge,
)
from arkitekt.cli.main import cli_app

from .isolation import isolated_filesystem

#: Pinned byte for byte: badges are pasted into READMEs and never updated. Orkestrator
#: builds and pins the same string (`kabinet/repoLink.test.ts`): change both or neither.
BADGE = (
    "[![Open in Arkitekt](https://arkitekt.live/img/badge/open-in-arkitekt.svg)]"
    "(https://arkitekt.live/deeplink?orkestrator=%2Fdo%2Fv1%2Frepo.install%3Fsource%3Doci%253Aghcr.io%252Fjhnnsrs%252Fbasiks)"
)


def test_the_badge_is_orkestrators_byte_for_byte():
    assert install_path("ghcr.io/jhnnsrs/basiks") == "/do/v1/repo.install?source=oci%3Aghcr.io%2Fjhnnsrs%2Fbasiks"
    assert install_badge("ghcr.io/jhnnsrs/basiks") == BADGE


@pytest.mark.parametrize(
    ("raw", "reference"),
    [
        ("ghcr.io/Jhnnsrs/Basiks", "ghcr.io/jhnnsrs/basiks"),
        (" https://ghcr.io/a/b/ ", "ghcr.io/a/b"),
        ("oci://ghcr.io/a/b", "ghcr.io/a/b"),
        ("localhost:5000/a/b", "localhost:5000/a/b"),
        ("jhnnsrs/basiks", "jhnnsrs/basiks"),
    ],
)
def test_a_reference_is_read_as_kabinet_reads_it(raw: str, reference: str):
    assert normalize_reference(raw) == reference


@pytest.mark.parametrize("raw", ["", "ghcr.io/a/b:latest", "ghcr.io/a/b@sha256:0", "ghcr.io/a//b", "ghcr.io/-a/b"])
def test_a_tag_a_digest_or_a_bad_segment_is_refused(raw: str):
    with pytest.raises(ValueError):
        normalize_reference(raw)


@pytest.mark.parametrize(
    ("remote", "package"),
    [
        ("https://github.com/Arkitektio/Basiks.git", "ghcr.io/arkitektio/basiks"),
        ("https://github.com/arkitektio/basiks", "ghcr.io/arkitektio/basiks"),
        ("git@github.com:arkitektio/basiks.git", "ghcr.io/arkitektio/basiks"),
        ("ssh://git@github.com/arkitektio/basiks.git", "ghcr.io/arkitektio/basiks"),
        ("https://gitlab.com/arkitektio/basiks.git", None),
        (None, None),
    ],
)
def test_the_package_is_the_one_the_workflow_publishes_for_a_github_remote(remote: str | None, package: str | None):
    assert package_for_remote(remote) == package


def test_the_badge_goes_under_the_first_heading_and_is_replaced_in_place(tmp_path: Path):
    readme = tmp_path / "README.md"
    readme.write_text("# basiks\n\nWhat it does.\n")
    assert write_badge(str(readme), PLACEHOLDER)
    assert readme.read_text() == f"# basiks\n\n{START}\n{PLACEHOLDER}\n{END}\n\nWhat it does.\n"

    assert write_badge(str(readme), BADGE, insert=False)
    assert readme.read_text() == f"# basiks\n\n{START}\n{BADGE}\n{END}\n\nWhat it does.\n"
    assert not write_badge(str(readme), BADGE, insert=False)


def test_a_readme_without_a_place_is_left_alone_unless_asked(tmp_path: Path):
    readme = tmp_path / "README.md"
    readme.write_text("No heading here.\n")
    assert not write_badge(str(readme), BADGE, insert=False)
    assert readme.read_text() == "No heading here.\n"
    assert write_badge(str(readme), BADGE)
    assert readme.read_text() == f"{START}\n{BADGE}\n{END}\n\nNo heading here.\n"
    assert write_badge(str(tmp_path / "NEW.md"), BADGE)
    assert (tmp_path / "NEW.md").read_text() == f"{START}\n{BADGE}\n{END}\n"


def test_the_command_prints_the_badge_for_a_package():
    with isolated_filesystem():
        result = CliRunner().invoke(cli_app, ["plugin", "badge", "--repository", "ghcr.io/Jhnnsrs/Basiks"])
        assert result.exit_code == 0, result.output
        assert result.output.strip() == BADGE


def test_the_command_reads_the_package_off_the_github_remote():
    with isolated_filesystem() as directory:
        subprocess.run(["git", "init", "-q"], cwd=directory, check=True)
        subprocess.run(
            ["git", "remote", "add", "origin", "git@github.com:jhnnsrs/basiks.git"], cwd=directory, check=True
        )
        (Path(directory) / "README.md").write_text("# basiks\n")
        result = CliRunner().invoke(cli_app, ["plugin", "badge", "--write"])
        assert result.exit_code == 0, result.output
        assert BADGE in (Path(directory) / "README.md").read_text()


def test_the_workflows_update_leaves_a_readme_without_a_place_alone():
    with isolated_filesystem() as directory:
        (Path(directory) / "README.md").write_text("# mine, no badge please\n")
        result = CliRunner().invoke(cli_app, ["plugin", "badge", "--update", "--repository", "ghcr.io/a/b"])
        assert result.exit_code == 0, result.output
        assert (Path(directory) / "README.md").read_text() == "# mine, no badge please\n"


def test_without_a_github_remote_the_command_says_what_to_pass():
    with isolated_filesystem():
        result = CliRunner().invoke(cli_app, ["plugin", "badge"])
        assert result.exit_code == 1
        assert "--repository" in " ".join(result.output.split())
