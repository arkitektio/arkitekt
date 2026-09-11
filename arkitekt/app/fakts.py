from typing import Optional

from fakts.cache.file import FileCache
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

    identifier = manifest.identifier
    version = manifest.version
    return FileCache(
        cache_file=f".arkitekt/cache/{identifier}-{version}_fakts_cache.json",
        hash=manifest.hash() + url,
    )


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
