import logging
import os
from hashlib import sha256
from typing import Optional

from platformdirs import user_state_dir

from arkitekt.app.options import ConnectionOptions
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

    It follows the user, beside the device id that already uses platformdirs,
    never the working directory: the same app run from two directories is one
    app with one session.

    The url is in the *filename*, not only in the cache's `hash=` binding.
    Without it, one app pointed at two servers (a lab and a local stack)
    would collide on one file, and since a different url invalidates the
    hash, each run would evict the other's session -- turning a shared path
    into a device-code prompt on every single start.
    """
    url_key = sha256(url.encode()).hexdigest()[:6]
    name = f"{manifest.identifier}-{manifest.version}-{url_key}_fakts_cache.json"
    return os.path.join(user_state_dir(APP_NAME, APP_AUTHOR), "cache", name)


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

    return FileCache(cache_file=cache_file, hash=manifest.hash() + url)


def build_device_code_fakts(
    manifest: Manifest,
    url: str,
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


def build_fakts(manifest: Manifest, options: ConnectionOptions) -> Fakts:
    """Build the fakts a run authenticates through, choosing the grant.

    Which grant applies is decided here, next to the three builders, rather than
    in the runtime: what is passed wins, then the environment, then a device code.

    Args:
        manifest: What the app tells the server it is, node id already resolved.
        options: How the run connects.

    Returns:
        The fakts, not yet entered.
    """
    from arkitekt.constants import DEFAULT_ARKITEKT_URL

    url = options.url or os.getenv("FAKTS_URL") or DEFAULT_ARKITEKT_URL
    token = options.token or os.getenv("FAKTS_TOKEN")
    redeem_token = options.redeem_token or os.getenv("FAKTS_REDEEM_TOKEN")

    if token:
        return build_token_fakts(
            manifest=manifest, token=token, url=url, no_cache=options.no_cache
        )
    if redeem_token:
        return build_redeem_fakts(
            manifest=manifest,
            redeem_token=redeem_token,
            url=url,
            no_cache=options.no_cache,
        )
    return build_device_code_fakts(
        manifest=manifest,
        url=url,
        no_cache=options.no_cache,
        headless=options.headless,
        device_code_hook=options.device_code_hook,
    )
