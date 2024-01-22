from herre.fakts.grant import FaktsGrant
from herre.fakts.registry import GrantRegistry, GrantType
from herre.grants.oauth2.authorization_code import AuthorizationCodeGrant
from herre.grants.oauth2.redirecters.aiohttp_server import AioHttpServerRedirecter
from herre.grants.oauth2.client_credentials import ClientCredentialsGrant


ARKITEKT_GRANT_REGISTRY = GrantRegistry()


def build_authorization_code_grant(**kwargs) -> FaktsGrant:
    return AuthorizationCodeGrant(**kwargs, redirecter=AioHttpServerRedirecter())


def build_client_credentials_grant(**kwargs) -> FaktsGrant:
    return ClientCredentialsGrant(**kwargs)


ARKITEKT_GRANT_REGISTRY.register_grant(
    GrantType.AUTHORIZATION_CODE,
    build_authorization_code_grant,
)

ARKITEKT_GRANT_REGISTRY.register_grant(
    GrantType.CLIENT_CREDENTIALS,
    build_client_credentials_grant,
)
