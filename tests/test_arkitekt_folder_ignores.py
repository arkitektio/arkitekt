"""What git leaves out of a project's ``.arkitekt/`` folder.

The folder holds what a project commits (its flavours) beside what it must not: the
credential JSONs and the rekuest agent's journal, a SQLite file with ``-wal`` and
``-shm`` files next to it.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest
from arkitekt.cli.commands.plugin.init import BUILD_CONTEXT_IGNORE
from arkitekt.utils import create_arkitekt_folder

JOURNAL = ["rekuest_journal.db", "rekuest_journal.db-wal", "rekuest_journal.db-shm"]

pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="needs git")


def _ignored(project: Path, *paths: str) -> set[str]:
    result = subprocess.run(
        ["git", "check-ignore", *paths], cwd=project, capture_output=True, text=True
    )
    return set(result.stdout.split())


@pytest.fixture
def project(tmp_path: Path) -> Path:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    return tmp_path


def test_the_journal_stays_out_of_git_and_the_flavours_do_not(project: Path) -> None:
    create_arkitekt_folder(base_dir=str(project))

    journal = [f".arkitekt/{name}" for name in JOURNAL]
    flavour = ".arkitekt/flavours/vanilla/Dockerfile"

    assert _ignored(project, *journal, ".arkitekt/token.json", flavour) == {
        *journal,
        ".arkitekt/token.json",
    }


def test_an_older_ignore_file_learns_what_it_lacks(project: Path) -> None:
    folder = project / ".arkitekt"
    folder.mkdir()
    # What arkitekt wrote before it knew of the journal, without a final newline.
    older = "# Hiding Arkitekt Credential files from git\n*.json\n*.temp\ncache/\nservers/"
    (folder / ".gitignore").write_text(older)

    create_arkitekt_folder(base_dir=str(project))
    create_arkitekt_folder(base_dir=str(project))

    content = (folder / ".gitignore").read_text()
    assert content.startswith(older + "\n")
    assert content.count("rekuest_journal.db*") == 1
    assert _ignored(project, ".arkitekt/rekuest_journal.db-wal")


def test_the_journal_never_reaches_an_image() -> None:
    assert ".arkitekt/rekuest_journal.db*" in BUILD_CONTEXT_IGNORE.splitlines()
