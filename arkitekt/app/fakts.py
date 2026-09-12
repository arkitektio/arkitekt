import logging
import os
from hashlib import sha256
from typing import Optional

from platformdirs import user_state_dir

from arkitekt.constants import APP_AUTHOR, APP_NAME
from fakts.cache.file import FileCache, ensure_private_dir
from fakts.cache.nocache import NoCache
from fakts.fakts import Fakts
from fakts.grants.remote import RemoteGrant
from fakts.grants.remote.authorizers.device_code import (
    ClientKind,
    DeviceCodeAuthorizer,
    DeviceCodeHook,
    display_in_terminal,
)
from fakts.grants.remote.authorizers.redeem import RedeemAuthorizer
from fakts.grants.remote.authorizers.static import StaticAuthorizer
from fakts.grants.remote.discovery.well_known import WellKnownDiscovery
from fakts.models import Manifest
from fakts.protocols import FaktsCache

logger = logging.getLogger(__name__)


def _cache_path(manifest: Manifest, url: str) -> str:
    """Where this app's session lives: one private per-user directory.

    The cache used to sit in `.arkitekt/cache/` relative to the *working
    directory*, which meant the same app run from two directories kept two
    sessions and re-authenticated on each first run. It now follows the user
    instead, beside the node id that already uses platformdirs.

    The url is in the *filename*, not only in the cache's `hash=` binding.
    Without it, one app pointed at two servers (a lab and a local stack)
    would collide on one file, and since a different url invalidates the
    hash, each run would evict the other's session -- turning a shared path
    into a device-code prompt on every single start.
    """
    url_key = sha256(url.encode()).hexdigest()[:6]
    name = f"{manifest.identifier}-{manifest.version}-{url_key}_fakts_cache.json"
    return os.path.join(user_state_dir(APP_NAME, APP_AUTHOR), "cache", name)


def _adopt_legacy_cache(manifest: Manifest, new_path: str) -> None:
    """Carry a pre-existing `./.arkitekt/cache/` session over, once.

    Relocating the cache would otherwise mean one silent re-authentication
    per app -- an interactive device-code prompt, which is exactly the thing
    this area is being fixed to stop provoking.

    Deliberately a plain copy at construction time rather than a read-through
    on the cache object: a read-through would have to hook the miss inside
    `Fakts.aget()`, where the load is async, and would need a wrapper cache
    to do it. There is also no hash check -- a stale legacy hash just reads
    as an ordinary miss on the next load, which is what would have happened
    anyway. The old file is left in place, so rolling this back keeps working.
    """
    legacy = os.path.join(
        ".arkitekt",
        "cache",
        f"{manifest.identifier}-{manifest.version}_fakts_cache.json",
    )
    if os.path.exists(new_path) or not os.path.exists(legacy):
        return

    try:
        with open(legacy, "rb") as source:
            payload = source.read()
        # O_EXCL: a sibling process may have adopted it a moment ago, and the
        # loser of that race must not truncate the winner's file.
        fd = os.open(new_path, os.O_CREAT | os.O_WRONLY | os.O_EXCL, 0o600)
        try:
            os.fchmod(fd, 0o600)  # os.open's mode is masked by the umask
            os.write(fd, payload)
        finally:
            os.close(fd)
    except OSError:
        logger.debug("Could not adopt the cache at %s.", legacy, exc_info=True)
        return

    logger.info(
        "Moved the cached session for %s from %s to %s.",
        manifest.identifier,
        legacy,
        new_path,
    )


def _build_cache(
    manifest: Manifest, url: str, no_cache: bool = False
) -> FaktsCache:
    """Cache the granted session per app and per server.

    Under fakts protocol v2 this file holds a live, rotating refresh token,
    not just configuration — so an app without a cache re-authenticates on
    every start.
    """
    if no_cache:
        return NoCache()

    cache_file = _cache_path(manifest, url)
    ensure_private_dir(os.path.dirname(cache_file))
    _adopt_legacy_cache(manifest, cache_file)

    return FileCache(cache_file=cache_file, hash=manifest.hash() + url)


def build_device_code_fakts(
    manifest: Manifest,
    url: Optional[str] = None,
    no_cache: bool = False,
    headless: bool = False,
    device_code_hook: Optional[DeviceCodeHook] = None,
    allow_insecure_transport: bool = False,
) -> Fakts:
    """Builds a Fakts instance for device code authentication.

    This is used when the user wants to authenticate an application
    using a device code. The user will be prompted to open a browser
    and approve the application once; the resulting session is cached.
    """
    if url is None:
        raise ValueError("URL must be provided")

    authorizer = DeviceCodeAuthorizer(
        manifest=manifest,
        open_browser=not headless,
        requested_client_kind=ClientKind.DEVELOPMENT,
        device_code_hook=device_code_hook if device_code_hook else display_in_terminal,
        allow_insecure_transport=allow_insecure_transport,
    )

    return Fakts(
        grant=RemoteGrant(
            authorizer=authorizer,
            discovery=WellKnownDiscovery(url=url, auto_protocols=["https", "http"]),
        ),
        manifest=manifest,
        cache=_build_cache(manifest, url, no_cache),
        allow_insecure_transport=allow_insecure_transport,
    )


def build_redeem_fakts(
    manifest: Manifest,
    redeem_token: str,
    url: str,
    no_cache: bool = False,
    allow_insecure_transport: bool = False,
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
        cache=_build_cache(manifest, url, no_cache),
        allow_insecure_transport=allow_insecure_transport,
    )


def build_token_fakts(
    manifest: Manifest,
    token: str,
    url: str,
    no_cache: bool = False,
    allow_insecure_transport: bool = False,
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
        cache=_build_cache(manifest, url, no_cache),
        allow_insecure_transport=allow_insecure_transport,
    )
