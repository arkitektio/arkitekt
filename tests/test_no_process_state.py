"""arkitekt keeps nothing ambient: a run is handed everything, and leaves the process alone.

Two apps in one process must not see each other through a context variable, and
a run must not reconfigure the process (logging) or write into the working
directory. Pinned here so the pattern cannot quietly return.
"""

import ast
from pathlib import Path

import arkitekt

PACKAGE = Path(arkitekt.__file__).parent
#: The command layer owns the process it runs in, so it may configure logging.
CLI = PACKAGE / "cli"


def _imports(tree: ast.Module) -> list[str]:
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.append(node.module)
    return found


def _library_modules() -> list[Path]:
    return [p for p in sorted(PACKAGE.rglob("*.py")) if CLI not in p.parents]


def test_no_module_uses_context_variables() -> None:
    offenders = [
        str(path.relative_to(PACKAGE))
        for path in sorted(PACKAGE.rglob("*.py"))
        if any(name.split(".")[0] == "contextvars" for name in _imports(ast.parse(path.read_text())))
    ]
    assert not offenders, f"context variables are back in: {offenders}"


def test_only_the_cli_configures_logging() -> None:
    offenders = [
        str(path.relative_to(PACKAGE))
        for path in _library_modules()
        if "basicConfig(" in path.read_text()
    ]
    assert not offenders, f"a run must not reconfigure logging: {offenders}"


def test_the_runtime_never_touches_the_working_directory() -> None:
    runtime = (PACKAGE / "runtime.py").read_text()
    assert "getcwd" not in runtime and "create_arkitekt_folder" not in runtime
