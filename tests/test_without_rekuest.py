"""arkitekt declares, inspects and connects without a runtime; only running needs one.

Each check runs in a subprocess that blocks ``rekuest`` from importing, so it proves
what an install without ``arkitekt[rekuest]`` can do -- whatever the test session
itself has loaded.
"""

import subprocess
import sys
import textwrap

BLOCK_REKUEST = """
import sys

class _NoRekuest:
    def find_spec(self, name, path=None, target=None):
        if name == "rekuest" or name.startswith("rekuest."):
            raise ImportError(f"blocked for the test: {name}")
        return None

sys.meta_path.insert(0, _NoRekuest())
"""


def _run(body: str) -> subprocess.CompletedProcess[str]:
    code = BLOCK_REKUEST + textwrap.dedent(body)
    return subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=False
    )


def test_arkitekt_imports_without_rekuest() -> None:
    """The package and its widgets import, and pull no rekuest module in."""
    result = _run(
        """
        import arkitekt, arkitekt.widgets
        assert not any(m.split(".")[0] == "rekuest" for m in sys.modules)
        print("ok")
        """
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "ok"


def test_an_app_declares_and_is_inspected_without_rekuest() -> None:
    """Declaring and inspecting (what `arkitekt inspect`/`plugin build` do) need no runtime."""
    result = _run(
        """
        from arkitekt import App, Task
        from arkitekt.cli.commands.app.inspect.utils import run_snapshot_or_exit
        from arkitekt.app.spec import app_declaration

        app = App("com.x", "1.0.0")

        @app.action
        def double(x: int, task: Task) -> int:
            return 2 * x

        run = run_snapshot_or_exit(app)
        declaration = app_declaration(app, run)
        print([i.definition.key for i in declaration.implementations])
        """
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "['double']"


def test_running_an_app_says_what_to_install() -> None:
    """`run()` fails before any login, naming the extra to install."""
    result = _run(
        """
        from arkitekt import App, run
        from arkitekt.runtime import RuntimeNotInstalledError

        app = App("com.x", "1.0.0")

        @app.action
        def double(x: int) -> int:
            return 2 * x

        try:
            run(app)
        except RuntimeNotInstalledError as e:
            print("hint:", "arkitekt[rekuest]" in str(e))
        """
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "hint: True"
