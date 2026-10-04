"""Serving an app over FastAPI: the same runtime as :func:`~arkitekt.run`, another agent.

``serve(app, fastapi_app)`` gives ``fastapi_app`` a lifespan that enters a
:class:`~arkitekt.runtime.Runtime` of ``app`` and provides its offerings over the
HTTP and websocket routes arkitekt-fastapi adds. The agent is the
runtime's: built after the app's clients, bound to the run, driven by it. An app
with no requirements authenticates nothing; one with services builds their
clients as any run does, and its actions are handed them by annotation.
"""

import asyncio
import contextlib
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any, Optional, Union, overload

from arkitekt_spec.declare.app import AppRegistry
from fakts.grants.remote.authorizers.device_code import DeviceCodeHook
from fakts.mesh import MeshOptions, MeshProxy

from arkitekt.app.app import App, Ctx
from arkitekt.app.options import ConnectionOptions
from arkitekt.runtime import Runtime

if TYPE_CHECKING:
    from fastapi import FastAPI


@overload
def serve(
    app: App[None],
    fastapi_app: "FastAPI",
    *,
    context: None = None,
    url: Optional[str] = None,
    token: Optional[str] = None,
    redeem_token: Optional[str] = None,
    skip_cache: bool = False,
    reauth: bool = False,
    headless: bool = False,
    device_code_hook: Optional[DeviceCodeHook] = None,
    allow_insecure_transport: bool = False,
    device_id: Optional[str] = None,
    mesh: Optional[Union[MeshOptions, MeshProxy, bool]] = None,
    **fastapi_options: Any,  # noqa: ANN401
) -> Runtime[None]: ...
@overload
def serve(
    app: App[Ctx],
    fastapi_app: "FastAPI",
    *,
    context: Ctx,
    url: Optional[str] = None,
    token: Optional[str] = None,
    redeem_token: Optional[str] = None,
    skip_cache: bool = False,
    reauth: bool = False,
    headless: bool = False,
    device_code_hook: Optional[DeviceCodeHook] = None,
    allow_insecure_transport: bool = False,
    device_id: Optional[str] = None,
    mesh: Optional[Union[MeshOptions, MeshProxy, bool]] = None,
    **fastapi_options: Any,  # noqa: ANN401
) -> Runtime[Ctx]: ...


def serve(
    app: App[Any],
    fastapi_app: "FastAPI",
    *,
    context: Any | None = None,  # noqa: ANN401
    url: Optional[str] = None,
    token: Optional[str] = None,
    redeem_token: Optional[str] = None,
    skip_cache: bool = False,
    reauth: bool = False,
    headless: bool = False,
    device_code_hook: Optional[DeviceCodeHook] = None,
    allow_insecure_transport: bool = False,
    device_id: Optional[str] = None,
    mesh: Optional[Union[MeshOptions, MeshProxy, bool]] = None,
    **fastapi_options: Any,  # noqa: ANN401
) -> Runtime[Any]:
    """Provide ``app``'s offerings over ``fastapi_app`` for as long as it runs.

    ::

        fastapi_app = FastAPI()
        serve(app, fastapi_app, context=config)
        uvicorn.run(fastapi_app)

    Args:
        app: The app to serve.
        fastapi_app: The FastAPI app to add the agent's routes and lifespan to.
        context: The app context: an instance of the class the app declared
            (``App(..., app_context=Config)``); required then, nothing otherwise.
        url: The fakts server, when the app has requirements. Defaults to
            ``$FAKTS_URL``, then the public deployment.
        token: A previously issued credential, ``client_id:refresh_token``.
        redeem_token: A token to provision a new app with.
        skip_cache: Neither read nor write the fakts cache: log in, and keep the
            session in memory only.
        reauth: Log in again even when a session is cached, and cache the new
            one. Defaults to ``$ARKITEKT_REAUTH``.
        headless: Print the device-code prompt instead of opening a browser.
        device_code_hook: Called with the login to approve -- a
            :class:`~arkitekt.DeviceCodeChallenge` carrying the code and the link --
            instead of the terminal prompt.
        allow_insecure_transport: Talk plain http to a server that is not on this
            machine. Off, such a server is refused.
        device_id: This device's identity. Defaults to the machine's id.
        mesh: How to reach services only on the deployment's mesh:
            ``MeshOptions()`` or ``True`` runs a node in this process (``arkitekt[mesh]``),
            ``MeshProxy(url=...)`` goes through a running proxy, ``False`` is off.
            Defaults to ``$ARKITEKT_MESH_PROXY``, then ``$ARKITEKT_MESH``; unset, the
            mesh is used when it is available (see :func:`arkitekt.app.fakts.mesh_from_env`).
        **fastapi_options: Passed on to
            :func:`arkitekt_fastapi.configure_fastapi` (``db_file``,
            ``expand_user_from_request``, the route paths, ...).

    Returns:
        The runtime, not yet entered: the lifespan enters it. It is what the
        served agent belongs to, and what ``inspect`` reads.

    Raises:
        AppContextError: If ``context`` is not what the app declared; here, not
            when the server starts.
    """
    app.registry.require_app_context(context, whose=f"App {app.identifier!r}")
    from arkitekt_fastapi import FastApiAgent
    from arkitekt_fastapi.routes import configure_fastapi
    from rath.task import task_scope

    registry = AppRegistry()

    @registry.provider()
    def fastapi_agent(registry: AppRegistry) -> FastApiAgent:
        """The agent serving the run's snapshot over ``fastapi_app``."""
        agent = configure_fastapi(
            fastapi_app, app_registry=registry, lifespan=False, **fastapi_options
        )
        # The runtime core knows no client library; rath's scope is what makes the
        # clients an action is handed attribute their requests to its task.
        agent.task_scopes.append(task_scope)
        return agent

    runtime = Runtime(
        app=app,
        options=ConnectionOptions(
            url=url,
            token=token,
            redeem_token=redeem_token,
            skip_cache=skip_cache,
            reauth=reauth,
            headless=headless,
            device_code_hook=device_code_hook,
            allow_insecure_transport=allow_insecure_transport,
            device_id=device_id,
            mesh=mesh,
        ),
        provider=fastapi_agent,
    )

    @contextlib.asynccontextmanager
    async def lifespan(_: "FastAPI") -> AsyncIterator[None]:
        async with runtime:
            providing = asyncio.create_task(runtime.arun(context=context))
            try:
                yield
            finally:
                providing.cancel()
                await asyncio.gather(providing, return_exceptions=True)

    fastapi_app.router.lifespan_context = lifespan
    return runtime


__all__ = ["serve"]
