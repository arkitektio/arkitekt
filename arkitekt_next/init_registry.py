import contextvars
from functools import wraps
from typing import Callable, Dict, Optional, TypeVar, overload
from .app import App

Params = Dict[str, str]


current_init_hook_registry = contextvars.ContextVar(
    "current_init_hook_registry", default=None
)


InitHook = Callable[[App], None]


class InitHookRegistry:
    """A registry for init hooks. This is used to register init hooks that
    are called when the app is initialized. The init hooks are called in
    the order they are registered

    The purpose of init hooks is to allow specific initialization
    code to be run when the app is initialized. This is useful if you
    plan to add some custom configuration or setup code that needs to be
    run before the app is getting conneted to the server.

    """

    def __init__(self) -> None:
        """Initialize the InitHookRegistry."""
        self.init_hooks: Dict[str, InitHook] = {}
        self.cli_only_hooks: Dict[str, InitHook] = {}

    def register(
        self,
        function: InitHook,
        name: Optional[str] = None,
        only_cli: bool = False,
    ) -> None:
        """Register a function as an init hook. This function will be called


        when the app is initialized. The init hooks are called in the order


        """

        if name is None:
            name = function.__name__

        # A hook lives in exactly one dict: cli_only_hooks only run when
        # run_all(is_cli=True), init_hooks always run.
        if only_cli:
            if name in self.cli_only_hooks:
                raise ValueError(f"CLI Hook {name} already registered")
            self.cli_only_hooks[name] = function
        else:
            if name in self.init_hooks:
                raise ValueError(f"Init Hook {name} already registered")
            self.init_hooks[name] = function

    def run_all(self, app: App, is_cli: bool = False) -> None:
        """ Run all registered init hooks."""
        for hook in self.init_hooks.values():
            hook(app)

        if is_cli:
            for hook in self.cli_only_hooks.values():
                hook(app)


T = TypeVar("T", bound=InitHook)


@overload
def init(func: T) -> T: ...


@overload
def init(
    *, only_cli: bool = False, init_hook_registry: InitHookRegistry | None = None
) -> Callable[[T], T]: ...


def init(
    func: T | None = None,
    *,
    only_cli: bool = False,
    init_hook_registry: InitHookRegistry | None = None,
) -> T | Callable[[T], T]:
    """Register a function as an init hook. This function will be called when the app is initialized."""
    init_hook_registry = init_hook_registry or get_default_init_hook_registry()

    if func is not None:
        init_hook_registry.register(func, only_cli=only_cli)
        setattr(func, "__is_init_hook__", True)
        return func

    def decorator(inner: T) -> T:
        @wraps(inner)
        def wrapped(app: App) -> None:
            return inner(app)

        init_hook_registry.register(wrapped, only_cli=only_cli)
        setattr(inner, "__is_init_hook__", True)
        return inner

    return decorator


GLOBAL_INIT_HOOK_REGISTRY = None


def get_default_init_hook_registry()-> InitHookRegistry:
    """Get the default init hook registry. This is used to register init hooks
    that are called when the app is initialized. If no registry is set, a new
    registry is created and returned.
    """
    global GLOBAL_INIT_HOOK_REGISTRY
    if GLOBAL_INIT_HOOK_REGISTRY is None:
        GLOBAL_INIT_HOOK_REGISTRY = InitHookRegistry()  # type: ignore
    return GLOBAL_INIT_HOOK_REGISTRY
