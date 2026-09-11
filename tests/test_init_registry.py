"""Tests for the init-hook registry, notably the only_cli exclusivity fix."""

from arkitekt.init_registry import InitHookRegistry


def test_cli_only_hook_registers_only_once():
    """A CLI-only hook must live only in cli_only_hooks (regression: it used to
    also fall through into init_hooks and run in non-CLI contexts)."""
    registry = InitHookRegistry()

    def my_cli_hook(app):
        pass

    registry.register(my_cli_hook, only_cli=True)

    assert "my_cli_hook" in registry.cli_only_hooks
    assert "my_cli_hook" not in registry.init_hooks


def test_run_all_respects_is_cli():
    registry = InitHookRegistry()
    calls = []

    registry.register(lambda app: calls.append("always"), name="always")
    registry.register(lambda app: calls.append("cli"), name="cli", only_cli=True)

    registry.run_all(app=None, is_cli=False)
    assert calls == ["always"]

    calls.clear()
    registry.run_all(app=None, is_cli=True)
    assert calls == ["always", "cli"]
