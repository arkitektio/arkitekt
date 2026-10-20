import logging
import os
from typing import Optional

from pydantic import SecretStr

from fakts.cache.file import FileCache, ensure_private_dir
from fakts.cache.nocache import NoCache
from fakts.fakts import Fakts
from fakts.grants.remote import RemoteGrant
from fakts.grants.remote.authorizers.device_code import (
    ClientKind,
    DeviceCodeAuthorizer,
    DeviceCodeHook,
)
from fakts.grants.remote.authorizers.mandate_key import MandateKeyAuthorizer
from fakts.grants.remote.authorizers.static import StaticAuthorizer
from fakts.grants.remote.discovery.well_known import WellKnownDiscovery
from fakts.grants.remote.models import FaktsEndpoint
from fakts.mesh import MeshOptions, MeshProxy
from fakts.models import ActiveFakts, Manifest
from fakts.protocols import FaktsCache

from arkitekt.app.options import ConnectionOptions
from arkitekt.app.sources import DISCOVER, Source, as_bool, cascade, from_argv, is_source, resolve
from arkitekt.app.sessions import session_path
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
    if device_code_hook is None:
        # Ours, not fakts' boxed one: a run asks in the look of the rest of it.
        # Imported here: the terminal is rich, which a host showing the login in
        # its own interface never needs.
        from arkitekt.app.terminal import logged_in, login_prompt

        device_code_hook, granted_hook = login_prompt(opened_browser=not headless), logged_in
    else:
        # Whoever shows the login says how it went: nothing is printed for them.
        granted_hook = _granted_quietly
    authorizer = DeviceCodeAuthorizer(
        manifest=manifest,
        open_browser=not headless,
        requested_client_kind=ClientKind.DEVELOPMENT,
        device_code_hook=device_code_hook,
        granted_hook=granted_hook,
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


async def _granted_quietly(endpoint: FaktsEndpoint, token: str) -> None:
    """The granted hook of a run whose host shows the login itself."""


def build_mandate_key_fakts(
    manifest: Manifest,
    mandate_key: str,
    url: str,
    skip_cache: bool = False,
    reauth: bool = False,
    allow_insecure_transport: bool = False,
    mesh: MeshOptions | MeshProxy | None = None,
) -> Fakts:
    """Builds a Fakts instance that logs in with a mandate key.

    The headless path: no browser, no user. Deployed containers, CI runners and
    the apps a hub or a deployer runs get one of these instead of a device code.
    There is no refresh token: the app logs in again with the key whenever its
    access token runs out.
    """
    return Fakts(
        grant=RemoteGrant(
            authorizer=MandateKeyAuthorizer(
                key=SecretStr(mandate_key),
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
    ``--mandate-key`` instead.
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
_MESH_FORCE = ("force", "only")
_MESH_AUTO = ("", "auto")


def mesh_from_env() -> MeshOptions | MeshProxy | None:
    """The mesh the environment asks for, as the Rust client reads it.

    ``ARKITEKT_MESH_PROXY=<url>`` goes through that running proxy. Otherwise
    ``ARKITEKT_MESH``: unset or ``auto`` uses the mesh when it is available
    (the bindings are installed and the server granted a key) and stays quiet
    when not; ``1`` (or ``native``) runs a node and reports what is missing;
    ``0`` turns it off; ``force`` uses the mesh and nothing else (aliases
    that are not on it are not tried). A proxy wins when both are set: it is
    the more specific instruction -- but ``ARKITEKT_MESH=force`` still makes
    it the only way taken.

    Raises:
        ValueError: ``ARKITEKT_MESH`` is set to something unrecognised -- a
            typo there would otherwise silently pick a mode.
    """
    return parse_mesh(os.getenv("ARKITEKT_MESH", ""), os.getenv("ARKITEKT_MESH_PROXY"))


def parse_mesh(text: str, proxy: str | None = None, *, what: str = "ARKITEKT_MESH") -> MeshOptions | MeshProxy | None:
    """A mesh mode as ``ARKITEKT_MESH`` (or ``--mesh``) spells it; ``proxy`` wins when given.

    ``--mesh`` may also name a running proxy itself (anything with ``://``).
    """
    value = text.strip().lower()
    if "://" in value:
        return MeshProxy(url=text.strip())
    if proxy:
        return MeshProxy(url=proxy, force=value in _MESH_FORCE)
    if value in _MESH_FORCE:
        return MeshOptions(force=True)
    if value in _MESH_AUTO:
        return MeshOptions(auto=True)
    if value in _MESH_ON:
        return MeshOptions()
    if value in _MESH_OFF:
        return None
    raise ValueError(
        f"{what}={value!r} is not understood: use auto (the default), 1/native "
        f"to always run a mesh node, force to use nothing but the mesh, 0 to turn it "
        f"off, or set ARKITEKT_MESH_PROXY=<url> "
        f"to use a running proxy."
    )


def forced_mesh() -> MeshOptions | MeshProxy:
    """The mesh as the only way to the services (``--force-mesh``): through
    the proxy the environment names, if it names one, or a node of our own."""
    proxy = os.getenv("ARKITEKT_MESH_PROXY")
    return MeshProxy(url=proxy, force=True) if proxy else MeshOptions(force=True)


def resolve_mesh(mesh: MeshOptions | MeshProxy | bool | Source | None = DISCOVER) -> MeshOptions | MeshProxy | None:
    """The mesh a run uses.

    A value wins (``True`` is ``MeshOptions()``; ``False`` and ``None`` are off). A source
    looks, in its order, at ``--mesh``, then ``$ARKITEKT_MESH_PROXY`` / ``$ARKITEKT_MESH``
    (:func:`mesh_from_env`), then the default: the mesh when it is available.
    """
    if not is_source(mesh):
        if mesh is True:
            return MeshOptions()
        if mesh is False or mesh is None:
            return None
        return mesh
    for source in cascade(mesh):
        if source == "arg":
            text = from_argv("mesh")
            if text is not None:
                return parse_mesh(text, what="--mesh")
        elif source == "env":
            if os.getenv("ARKITEKT_MESH", "").strip() or os.getenv("ARKITEKT_MESH_PROXY"):
                return mesh_from_env()
        elif source == "default":
            return MeshOptions(auto=True)
    return None


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


def resolve_url(url: str | Source | None = DISCOVER) -> str:
    """The fakts server a run connects to: a URL as given, or from its source
    (``"discover"``: ``--url``, then ``$FAKTS_URL``, then the public deployment).

    A run cannot connect to no server, so ``None`` is read as ``"discover"``.
    Surrounding whitespace and a trailing slash are dropped: a session is saved
    per server by this string, and ``https://lab/`` is the server ``https://lab``.

    Raises:
        ValueError: The source names no default and found no URL.
    """
    found = resolve(DISCOVER if url is None else url, flag="url", env="FAKTS_URL", default=lambda: DEFAULT_ARKITEKT_URL, parse=str)
    if not found:
        raise ValueError(f"No fakts server: nothing at {url!r} (--url, $FAKTS_URL).")
    return found.strip().rstrip("/")


def resolve_token(token: str | Source | None = DISCOVER) -> str | None:
    """A previously issued credential: as given, or ``--token`` / ``$FAKTS_TOKEN``."""
    return resolve(token, flag="token", env="FAKTS_TOKEN", default=lambda: None, parse=str) or None


def resolve_mandate_key(mandate_key: str | Source | None = DISCOVER) -> str | None:
    """A token to provision with: as given, or ``--mandate-key`` / ``$FAKTS_MANDATE_KEY``."""
    return resolve(mandate_key, flag="mandate-key", env="FAKTS_MANDATE_KEY", default=lambda: None, parse=str) or None


def resolve_reauth(reauth: bool | Source = DISCOVER) -> bool:
    """Whether to log in again: as given, or ``--reauth`` / ``$ARKITEKT_REAUTH`` / off."""
    return bool(resolve(reauth, flag="reauth", env="ARKITEKT_REAUTH", default=lambda: False, parse=lambda text: as_bool(text, what="ARKITEKT_REAUTH (or --reauth)"), boolean=True))


INSECURE_TRANSPORT_ENV = "FAKTS_ALLOW_INSECURE_TRANSPORT"


def resolve_insecure_transport(allow: bool | Source = DISCOVER) -> bool:
    """Whether plain http to another machine is allowed: as given, or
    ``--allow-insecure-transport`` / ``$FAKTS_ALLOW_INSECURE_TRANSPORT`` / off.

    fakts itself still honours the variable as an opt-in, whatever is passed here.
    """
    return bool(
        resolve(allow, flag="allow-insecure-transport", env=INSECURE_TRANSPORT_ENV, default=lambda: False, parse=lambda text: as_bool(text, what="FAKTS_ALLOW_INSECURE_TRANSPORT (or --allow-insecure-transport)"), boolean=True)
    )


def build_fakts(manifest: Manifest, options: ConnectionOptions) -> Fakts:
    """Build the fakts a run authenticates through, choosing the grant.

    Which grant applies is decided here, next to the three builders, rather than
    in the runtime: what is passed wins, then the environment, then a device code.
    Each option is a value or a source (see :mod:`arkitekt.app.sources`); ``reauth``
    logs in again and caches the result.

    Args:
        manifest: What the app tells the server it is, node id already resolved.
        options: How the run connects.

    Returns:
        The fakts, not yet entered.
    """
    url = resolve_url(options.url)
    token = resolve_token(options.token)
    mandate_key = resolve_mandate_key(options.mandate_key)
    mesh = resolve_mesh(options.mesh)
    reauth = resolve_reauth(options.reauth)
    allow_insecure_transport = resolve_insecure_transport(options.allow_insecure_transport)

    if token:
        return build_token_fakts(
            manifest=manifest,
            token=token,
            url=url,
            skip_cache=options.skip_cache,
            reauth=reauth,
            allow_insecure_transport=allow_insecure_transport,
            mesh=mesh,
        )
    if mandate_key:
        return build_mandate_key_fakts(
            manifest=manifest,
            mandate_key=mandate_key,
            url=url,
            skip_cache=options.skip_cache,
            reauth=reauth,
            allow_insecure_transport=allow_insecure_transport,
            mesh=mesh,
        )
    return build_device_code_fakts(
        manifest=manifest,
        url=url,
        skip_cache=options.skip_cache,
        reauth=reauth,
        headless=options.headless,
        device_code_hook=options.device_code_hook,
        allow_insecure_transport=allow_insecure_transport,
        mesh=mesh,
    )
