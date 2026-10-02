"""What a run says in the terminal on its own: the login prompt, in the CLI's look."""

import asyncio

from fakts.grants.remote.models import FaktsEndpoint

from arkitekt.app.fakts import build_device_code_fakts
from arkitekt.app.terminal import logged_in, login_prompt

from .test_cache_paths import make_manifest

ENDPOINT = FaktsEndpoint(
    base_url="https://lab.example/f/",
    name="Lab",
    configure="https://lab.example/f/device/?code={code}",
)


def _flat(output: str) -> str:
    return " ".join(output.split())


def test_the_prompt_links_to_the_approval_page_with_the_code_filled_in(capsys) -> None:
    asyncio.run(login_prompt(opened_browser=True)(ENDPOINT, "ABCD-EFGH"))

    out = capsys.readouterr().out
    assert out.startswith("■ Log in to Lab")
    assert "opened in your browser" in out
    assert "https://lab.example/f/device/?code=ABCD-EFGH" in out
    assert "code ABCD-EFGH" in out
    assert "│" not in out and "╭" not in out


def test_a_headless_prompt_asks_for_the_link_to_be_opened(capsys) -> None:
    asyncio.run(login_prompt(opened_browser=False)(ENDPOINT, "ABCD-EFGH"))

    assert "open this link to approve the app" in _flat(capsys.readouterr().out)


def test_an_endpoint_without_an_approval_page_gets_its_address_and_the_code(capsys) -> None:
    bare = FaktsEndpoint(base_url="https://lab.example/f/", name="Lab")

    asyncio.run(login_prompt()(bare, "ABCD-EFGH"))

    out = capsys.readouterr().out
    assert "https://lab.example/f/" in out and "code ABCD-EFGH" in out


def test_being_logged_in_never_shows_the_token(capsys) -> None:
    asyncio.run(logged_in(ENDPOINT, "SECRET-ACCESS"))

    out = capsys.readouterr().out
    assert out == "◆ Logged in to Lab\n"


def test_a_device_code_login_asks_and_confirms_in_our_look() -> None:
    """The builder hands fakts our prompt, not its boxed one, unless given another."""
    manifest = make_manifest()

    ours = build_device_code_fakts(manifest, "https://lab.example", skip_cache=True)
    authorizer = ours.grant.authorizer  # pyright: ignore[reportAttributeAccessIssue]
    assert authorizer.device_code_hook.__module__ == "arkitekt.app.terminal"
    assert authorizer.granted_hook is logged_in

    async def theirs(endpoint, code) -> None:  # noqa: ANN001
        return None

    given = build_device_code_fakts(
        manifest, "https://lab.example", skip_cache=True, device_code_hook=theirs
    )
    assert given.grant.authorizer.device_code_hook is theirs  # pyright: ignore[reportAttributeAccessIssue]
