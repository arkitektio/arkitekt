"""A temporary working directory for a CLI test, as click's runner used to give one.

``typer.testing.CliRunner`` (typer vendors its own click) has no
``isolated_filesystem``; commands that resolve files against the current working
directory run inside this instead.
"""

import contextlib
import tempfile
from collections.abc import Iterator


@contextlib.contextmanager
def isolated_filesystem() -> Iterator[str]:
    """Change into a fresh temporary directory for the block, and remove it after."""
    with tempfile.TemporaryDirectory() as directory, contextlib.chdir(directory):
        yield directory
