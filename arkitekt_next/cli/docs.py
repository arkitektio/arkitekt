"""Documentation links for the Arkitekt Next CLI.

These routes are kept as constants in one place so the hosted documentation can
be re-organized without touching any command code. Change :data:`DOCS_BASE_URL`
or any of the per-command routes below and every `--help` epilogue (and the
docs in ``docs/cli.md``) can be updated to match in a single edit.
"""

#: Base URL of the hosted Arkitekt documentation.
DOCS_BASE_URL = "https://arkitekt.live"

#: Section of the hosted docs that covers the CLI.
CLI_DOCS_BASE = f"{DOCS_BASE_URL}/docs/cli"

# --- Per-command documentation routes --------------------------------------
INIT_DOCS = f"{CLI_DOCS_BASE}/init"
RUN_DOCS = f"{CLI_DOCS_BASE}/run"
GEN_DOCS = f"{CLI_DOCS_BASE}/gen"
MANIFEST_DOCS = f"{CLI_DOCS_BASE}/manifest"
INSPECT_DOCS = f"{CLI_DOCS_BASE}/inspect"
CALL_DOCS = f"{CLI_DOCS_BASE}/call"
SELF_DOCS = f"{CLI_DOCS_BASE}/self"
APP_DOCS = f"{CLI_DOCS_BASE}/app"
PLUGIN_DOCS = f"{CLI_DOCS_BASE}/plugin"

MESH_DOCS = f"{CLI_DOCS_BASE}/mesh"

#: Conceptual guides referenced from multiple commands.
FLAVOURS_DOCS = f"{DOCS_BASE_URL}/docs/flavours"


def help_epilog(url: str) -> str:
    """Render a Typer/rich epilogue that links to the hosted docs for a command.

    Used as the ``epilog=`` of a command/group so that ``--help`` always points
    the user at the matching page on the hosted documentation.
    """
    return f"📖 Learn more: [link={url}]{url}[/link]"
