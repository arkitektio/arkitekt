"""Tests for the CLI documentation links / `--help` epilogues.

The hosted documentation routes live as constants in `arkitekt.cli.docs`.
These tests ensure the constants stay consistent and that each command group's
`--help` actually surfaces its link, so the crosslinking does not silently break.
"""

import pytest
from click.testing import CliRunner

from arkitekt.cli.main import cli
from arkitekt.cli import docs


def test_routes_build_on_base_url():
    """Every per-command route is derived from the configurable base URL."""
    assert docs.CLI_DOCS_BASE.startswith(docs.DOCS_BASE_URL)
    for route in (
        docs.INIT_DOCS,
        docs.RUN_DOCS,
        docs.GEN_DOCS,
        docs.PLUGIN_DOCS,
        docs.MANIFEST_DOCS,
        docs.INSPECT_DOCS,
        docs.CALL_DOCS,
    ):
        assert route.startswith(docs.CLI_DOCS_BASE)


def test_help_epilog_renders_a_link():
    epilog = docs.help_epilog(docs.INIT_DOCS)
    assert docs.INIT_DOCS in epilog
    assert "[link=" in epilog


@pytest.mark.parametrize(
    "args",
    [
        # SDK commands live at the root.
        ["init"],
        ["run"],
        ["gen"],
        ["manifest"],
        ["inspect"],
        ["call"],
        # Top-level groups.
        ["plugin"],
        ["mesh"],
        ["self"],
    ],
)
def test_help_includes_docs_link(args):
    result = CliRunner().invoke(cli, [*args, "--help"])
    assert result.exit_code == 0, result.output
    assert "Learn more" in result.output
    # rich-click may wrap long URLs across lines, so check the host at least.
    assert docs.DOCS_BASE_URL.split("//")[1] in result.output
