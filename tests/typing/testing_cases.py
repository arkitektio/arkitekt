"""Static cases for a test written against ``arkitekt.testing``.

Checked by basedpyright, not run. A line ending in ``# expect-error`` must be
reported; every other line must not.
"""

from typing import assert_type

from arkitekt import App
from arkitekt.runtime import Runtime
from arkitekt.testing import TestStack


class Config:
    gain: float = 1.0


def a_stack_knows_its_apps_context(teststack: TestStack[Config]) -> None:
    assert_type(teststack.app, App[Config])
    assert_type(teststack.runtime, Runtime[Config])
    teststack.runtime.run(Config())
    teststack.runtime.run("not the context")  # expect-error


def a_stack_of_an_app_without_a_context(teststack: TestStack[None]) -> None:
    assert_type(teststack.app, App[None])
    assert_type(teststack.runtime, Runtime[None])
    teststack.runtime.run()
    teststack.runtime.run(Config())  # expect-error
