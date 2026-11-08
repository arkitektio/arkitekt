"""What a run says in the terminal on its own: the login prompt, in the CLI's look."""

import asyncio
import io
import re

from fakts.grants.remote.authorizers.device_code import DeviceCodeChallenge
from fakts.grants.remote.models import FaktsEndpoint
from rich.console import Console

from arkitekt.app.fakts import build_device_code_fakts
from arkitekt.app.terminal import QR_ENV, _qr, force_qr, logged_in, login_prompt

from .test_cache_paths import make_manifest

ENDPOINT = FaktsEndpoint(
    base_url="https://lab.example/f/",
    name="Lab",
    configure="https://lab.example/f/device/?code={code}",
)


def _challenge(endpoint: FaktsEndpoint, link: str) -> DeviceCodeChallenge:
    return DeviceCodeChallenge(
        endpoint=endpoint, user_code="ABCD-EFGH", verification_uri_complete=link, expires_in=300
    )


APPROVE = _challenge(ENDPOINT, "https://lab.example/f/device/?code=ABCD-EFGH")


def _flat(output: str) -> str:
    return " ".join(output.split())


def test_the_prompt_links_to_the_approval_page_with_the_code_filled_in(capsys, monkeypatch) -> None:
    monkeypatch.delenv(QR_ENV, raising=False)
    asyncio.run(login_prompt(opened_browser=True)(APPROVE))  # pyright: ignore[reportArgumentType]

    out = capsys.readouterr().out
    assert out.startswith("■ Log in to Lab")
    assert "opened in your browser" in out
    assert "https://lab.example/f/device/?code=ABCD-EFGH" in out
    assert "code ABCD-EFGH" in out
    assert "│" not in out and "╭" not in out
    assert "█" not in out, "the page opened here: no QR code to scan"


def test_a_headless_prompt_asks_for_the_link_to_be_opened(capsys, monkeypatch) -> None:
    monkeypatch.delenv(QR_ENV, raising=False)
    asyncio.run(login_prompt(opened_browser=False)(APPROVE))  # pyright: ignore[reportArgumentType]

    out = capsys.readouterr().out
    assert "open this link to approve the app" in _flat(out)
    assert "█" in out, "approved on another device: the link is a QR code too"


def test_a_forced_qr_code_is_drawn_even_for_a_local_page_that_opened(capsys, monkeypatch) -> None:
    monkeypatch.delenv(QR_ENV, raising=False)  # restored after the test: force_qr sets it
    force_qr()
    local = _challenge(ENDPOINT, "http://localhost:8000/f/device/?code=ABCD-EFGH")

    asyncio.run(login_prompt(opened_browser=True)(local))  # pyright: ignore[reportArgumentType]

    assert "█" in capsys.readouterr().out


LINK = "https://lab.example/f/device/?code=ABCD-EFGH"


def _drawn(width: int, color_system: str | None = "standard") -> str:
    out = io.StringIO()
    console = Console(file=out, force_terminal=True, color_system=color_system, width=width)  # pyright: ignore[reportArgumentType]
    _qr(console, LINK)
    return out.getvalue()


def _modules(border: int = 4) -> list[list[bool]]:
    import segno

    return [[bool(m) for m in row] for row in segno.make_qr(LINK, error="l").matrix_iter(border=border)]


def test_a_qr_code_is_painted_with_backgrounds_two_spaces_a_module() -> None:
    """No glyphs: a background fills the line height, so there are no seams to scan across."""
    drawn = _drawn(width=200)

    assert not set(drawn) & set("▀▄█")
    # Dark modules black, light ones bright white (not white: a grey in many themes).
    grid = [
        [code == "40" for code, spaces in re.findall(r"\x1b\[(\d+)m( +)", line) for _ in range(len(spaces) // 2)]
        for line in drawn.splitlines()
    ]
    assert set(re.findall(r"\x1b\[(\d+)m ", drawn)) == {"40", "107"}
    assert grid == _modules(), "every module, with a quiet zone of four"


def test_a_narrow_terminal_gets_half_blocks_coloured_above_and_below() -> None:
    modules = _modules()
    drawn = _drawn(width=2 * len(modules[0]))  # one column short of two a module, with the indent

    assert "▀" in drawn and "▄" not in drawn and "█" not in drawn
    cells = [re.findall(r"\x1b\[(\d+);(\d+)m(▀+)", line) for line in drawn.splitlines()]
    top = [[fg == "30" for fg, _, run in row for _ in run] for row in cells]
    bottom = [[bg == "40" for _, bg, run in row for _ in run] for row in cells]
    padded = modules + [[False] * len(modules[0])] * (len(modules) % 2)
    assert top == padded[::2] and bottom == padded[1::2]


def test_without_colours_a_qr_code_draws_its_light_modules() -> None:
    drawn = _drawn(width=200, color_system=None)

    assert "\x1b[" not in drawn
    assert "█" in drawn


def test_an_endpoint_without_an_approval_page_gets_its_address_and_the_code(capsys) -> None:
    bare = FaktsEndpoint(base_url="https://lab.example/f/", name="Lab")

    asyncio.run(login_prompt()(_challenge(bare, bare.base_url)))  # pyright: ignore[reportArgumentType]

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

    async def theirs(challenge: DeviceCodeChallenge) -> None:
        return None

    given = build_device_code_fakts(
        manifest, "https://lab.example", skip_cache=True, device_code_hook=theirs
    )
    assert given.grant.authorizer.device_code_hook is theirs  # pyright: ignore[reportAttributeAccessIssue]
    # Whoever shows the login says how it went: nothing is printed for them.
    assert given.grant.authorizer.granted_hook is not logged_in  # pyright: ignore[reportAttributeAccessIssue]
