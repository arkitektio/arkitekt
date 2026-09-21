"""Static cases for the app context: checked by basedpyright, not run.

A line ending in ``# expect-error`` must be reported; every other line must not.
"""

from typing import assert_type

from arkitekt import App, connect, run
from arkitekt.runtime import Runtime


class Config:
    pass


assert_type(App("x"), App[None])
assert_type(App("x", app_context=Config), App[Config])
assert_type(connect(App("x", app_context=Config)), Runtime[Config])
assert_type(connect(App("x")), Runtime[None])

run(App("x"))
run(App("x", app_context=Config), context=Config())
run(App("x"), context=1)  # expect-error
run(App("x", app_context=Config))  # expect-error
run(App("x", app_context=Config), context="no")  # expect-error
