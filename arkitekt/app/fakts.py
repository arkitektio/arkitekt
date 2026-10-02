import logging
import os
from typing import Optional

from fakts.cache.file import FileCache, ensure_private_dir
from fakts.cache.nocache import NoCache
from fakts.fakts import Fakts
from fakts.grants.remote import RemoteGrant
from fakts.grants.remote.authorizers.device_code import (
    ClientKind,
    DeviceCodeAuthorizer,
    DeviceCodeHook,
)
from fakts.grants.remote.authorizers.redeem import RedeemAuthorizer
from fakts.grants.remote.authorizers.static import StaticAuthorizer
from fakts.grants.remote.discovery.well_known import WellKnownDiscovery
from fakts.mesh import MeshOptions, MeshProxy
from fakts.models import ActiveFakts, Manifest
from fakts.protocols import FaktsCache

from arkitekt.app.options import ConnectionOptions
from arkitekt.app.sessions import session_path
from arkitekt.app.terminal import logged_in, login_prompt
from arkitekt.constants import DEFAULT_ARKITEKT_URL

logger = logging.getLogger(__name__)


def _cache_path(manifest: Manifest, url: str) -> str:
    """Where this app's session lives (see :func:`arkitekt.app.sessions.session_path`)."""
    return session_path(manifest.identifier, manifest.version, url)


def _build_cache(
    manifest: Manifest, url: str, skip_cache: bool = False, reauth: bool = False
) -> FaktsCache:
    """Cache the granted session per app and per server.

    Under fakts protocol v2 this file holds a live, rotating refresh token,
    not just configuration — so an app without a cache re-authenticates on
    every start. ``skip_cache`` keeps the session in memory only; ``reauth``
    ignores the cached session but still caches the new one.
    """
    if skip_cache:
        return NoCache()

    cache_file = _cache_path(manifest, url)
    ensure_private_dir(os.path.dirname(cache_file))

    cache = FileCache(cache_file=cache_file, hash=manifest.hash() + url)
    return ReauthCache(cache=cache) if reauth else cache


class ReauthCache(FaktsCache):
    """A cache that hides what it held until this run has written to it.

    The first load misses, so the grant runs and a fresh login happens; its
    result is written through, and from then on every read and write goes to
    the wrapped cache as usual -- fakts re-reads the cache mid-run to adopt
    sibling rotations and to refuse stale writes, which must keep working.
    Nothing is deleted up front: a login that fails leaves the old session.
    """

    def __init__(self, cache: FaktsCache) -> None:
        self.cache = cache
        self.written = False

    async def aload(self) -> ActiveFakts | None:
        """Miss until this run wrote a session, then read through."""
        if not self.written:
            return None
        return await self.cache.aload()

    async def aset(self, value: ActiveFakts) -> None:
        """Write through, and stop hiding the cache."""
        await self.cache.aset(value)
        self.written = True

    async def areset(self) -> None:
        """Reset the wrapped cache."""
        await self.cache.areset()


def build_device_code_fakts(
    manifest: Manifest,
    url: str,
    skip_cache: bool = False,
    reauth: bool = False,
    headless: bool = False,
    device_code_hook: Optional[DeviceCodeHook] = None,
    allow_insecure_transport: bool = False,
    mesh: MeshOptions | MeshProxy | None = None,
) -> Fakts:
    """Builds a Fakts instance for device code authentication.

    This is used when the user wants to authenticate an application
    using a device code. The user will be prompted to open a browser
    and approve the application once; the resulting session is cached.
    """
    authorizer = DeviceCodeAuthorizer(
        manifest=manifest,
        open_browser=not headless,
        requested_client_kind=ClientKind.DEVELOPMENT,
        # Ours, not fakts' boxed one: a run asks in the look of the rest of it.
        device_code_hook=device_code_hook or login_prompt(opened_browser=not headless),
        granted_hook=logged_in,
        allow_insecure_transport=allow_insecure_transport,
        # Only a node of our own needs a key to join with; a proxy is already on the mesh.
        request_auth_key=isinstance(mesh, MeshOptions) and mesh.requests_key(),
    )

    return Fakts(
        grant=RemoteGrant(
            authorizer=authorizer,
            discovery=WellKnownDiscovery(url=url, auto_protocols=["https", "http"]),
        ),
        manifest=manifest,
        cache=_build_cache(manifest, url, skip_cache, reauth),
        allow_insecure_transport=allow_insecure_transport,
        mesh=mesh,
    )


def build_redeem_fakts(
    manifest: Manifest,
    redeem_token: str,
    url: str,
    skip_cache: bool = False,
    reauth: bool = False,
    allow_insecure_transport: bool = False,
    mesh: MeshOptions | MeshProxy | None = None,
) -> Fakts:
    """Builds a Fakts instance that redeems a provisioning token.

    The headless path: no browser, no user. Deployed containers and CI
    runners get one of these instead of a device code.
    """
    return Fakts(
        grant=RemoteGrant(
            authorizer=RedeemAuthorizer(
                token=redeem_token,
                manifest=manifest,
                allow_insecure_transport=allow_insecure_transport,
            ),
            discovery=WellKnownDiscovery(url=url, auto_protocols=["https", "http"]),
        ),
        manifest=manifest,
        cache=_build_cache(manifest, url, skip_cache, reauth),
        allow_insecure_transport=allow_insecure_transport,
        mesh=mesh,
    )


def build_token_fakts(
    manifest: Manifest,
    token: str,
    url: str,
    skip_cache: bool = False,
    reauth: bool = False,
    allow_insecure_transport: bool = False,
    mesh: MeshOptions | MeshProxy | None = None,
) -> Fakts:
    """Builds a Fakts instance from a credential issued earlier.

    ``token`` is a ``client_id:refresh_token`` pair. A bare refresh token
    will not work: the token endpoint authenticates the client before it
    validates the token, so both halves have to travel together.

    Under protocol v1 this flag carried a *claim* token, which was traded at
    an endpoint that no longer exists. If you were passing one of those, use
    ``--redeem-token`` instead.
    """
    return Fakts(
        grant=RemoteGrant(
            authorizer=StaticAuthorizer(
                token=token,
                allow_insecure_transport=allow_insecure_transport,
            ),
            discovery=WellKnownDiscovery(url=url, auto_protocols=["https", "http"]),
        ),
        manifest=manifest,
        cache=_build_cache(manifest, url, skip_cache, reauth),
        allow_insecure_transport=allow_insecure_transport,
        mesh=mesh,
    )


_MESH_ON = ("1", "true", "yes", "on", "native")
_MESH_OFF = ("0", "false", "no", "off")
_MESH_AUTO = ("", "auto")


def mesh_from_env() -> MeshOptions | MeshProxy | None:
    """The mesh the environment asks for, as the Rust client reads it.

    ``ARKITEKT_MESH_PROXY=<url>`` goes through that running proxy. Otherwise
    ``ARKITEKT_MESH``: unset or ``auto`` uses the mesh when it is available
    (the bindings are installed and the server granted a key) and stays quiet
    when not; ``1`` (or ``native``) runs a node and reports what is missing;
    ``0`` turns it off. A proxy wins when both are set: it is the more
    specific instruction.

    Raises:
        ValueError: ``ARKITEKT_MESH`` is set to something unrecognised -- a
            typo there would otherwise silently pick a mode.
    """
    proxy = os.getenv("ARKITEKT_MESH_PROXY")
    if proxy:
        return MeshProxy(url=proxy)
    value = os.getenv("ARKITEKT_MESH", "").strip().lower()
    if value in _MESH_AUTO:
        return MeshOptions(auto=True)
    if value in _MESH_ON:
        return MeshOptions()
    if value in _MESH_OFF:
        return None
    raise ValueError(
        f"ARKITEKT_MESH={value!r} is not understood: use auto (the default), 1/native "
        f"to always run a mesh node, 0 to turn it off, or set ARKITEKT_MESH_PROXY=<url> "
        f"to use a running proxy."
    )


def resolve_mesh(mesh: MeshOptions | MeshProxy | bool | None) -> MeshOptions | MeshProxy | None:
    """What was passed wins (``True`` is ``MeshOptions()``, ``False`` is off);
    ``None`` defers to :func:`mesh_from_env`."""
    if mesh is None:
        return mesh_from_env()
    if mesh is True:
        return MeshOptions()
    if mesh is False:
        return None
    return mesh


_REAUTH_ON = ("1", "true", "yes", "on")
_REAUTH_OFF = ("", "0", "false", "no", "off")


def reauth_from_env() -> bool:
    """Whether ``ARKITEKT_REAUTH`` asks this run to log in again.

    The fresh session is still cached, so the next run without the variable
    reuses it (``skip_cache`` is the one that caches nothing).

    Raises:
        ValueError: ``ARKITEKT_REAUTH`` is set to something unrecognised -- a
            typo there would otherwise silently keep the old session.
    """
    value = os.getenv("ARKITEKT_REAUTH", "").strip().lower()
    if value in _REAUTH_ON:
        return True
    if value in _REAUTH_OFF:
        return False
    raise ValueError(
        f"ARKITEKT_REAUTH={value!r} is not understood: use 1 to log in again, 0 (or unset) "
        f"to reuse the cached session."
    )


def resolve_url(url: Optional[str] = None) -> str:
    """The fakts server a run connects to: what is passed, then ``$FAKTS_URL``,
    then the public deployment."""
    return url or os.getenv("FAKTS_URL") or DEFAULT_ARKITEKT_URL


def build_fakts(manifest: Manifest, options: ConnectionOptions) -> Fakts:
    """Build the fakts a run authenticates through, choosing the grant.

    Which grant applies is decided here, next to the three builders, rather than
    in the runtime: what is passed wins, then the environment, then a device code.
    ``reauth`` (or ``ARKITEKT_REAUTH=1``) logs in again and caches the result.

    Args:
        manifest: What the app tells the server it is, node id already resolved.
        options: How the run connects.

    Returns:
        The fakts, not yet entered.
    """
    url = resolve_url(options.url)
    token = options.token or os.getenv("FAKTS_TOKEN")
    redeem_token = options.redeem_token or os.getenv("FAKTS_REDEEM_TOKEN")
    mesh = resolve_mesh(options.mesh)
    reauth = options.reauth or reauth_from_env()

    if token:
        return build_token_fakts(
            manifest=manifest,
            token=token,
            url=url,
            skip_cache=options.skip_cache,
            reauth=reauth,
            mesh=mesh,
        )
    if redeem_token:
        return build_redeem_fakts(
            manifest=manifest,
            redeem_token=redeem_token,
            url=url,
            skip_cache=options.skip_cache,
            reauth=reauth,
            mesh=mesh,
        )
    return build_device_code_fakts(
        manifest=manifest,
        url=url,
        skip_cache=options.skip_cache,
        reauth=reauth,
        headless=options.headless,
        device_code_hook=options.device_code_hook,
        mesh=mesh,
    )
