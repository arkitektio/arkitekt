"""The ``mesh`` command group: join this machine to the Arkitekt WireGuard mesh.

An Arkitekt deployment can expose a private WireGuard mesh (an ionscale tailnet)
coordinated by a tailscale/headscale server, so that clients reach the services
over the mesh instead of the public internet.

`mesh join` uses the **mesh device-code flow**: this machine asks to join, a human
organization member authorizes it on a web page, and the machine then receives a
single-use pre-authorized key + coordination URL + machine name and runs
`tailscale up --authkey=…` to enroll. The endpoints for that flow are advertised in
the Fakts server's ``/.well-known/fakts`` document.
"""

import asyncio
import shutil
import socket
import subprocess
import time
import webbrowser
from pathlib import Path
from typing import Annotated, Any, Dict, List, Optional, Tuple

import typer
from rich.panel import Panel

from arkitekt.cli.errors import cli_error, confirm_or_abort
from arkitekt.cli.interactive import require_interactive
from arkitekt.cli.options import UrlOption
from arkitekt.cli.vars import get_console
from arkitekt.constants import DEFAULT_ARKITEKT_URL

#: Where to point users who do not have tailscale installed yet.
TAILSCALE_INSTALL_URL = "https://tailscale.com/download"
#: Reference for the ``tailscale up`` command this group drives.
TAILSCALE_UP_DOCS_URL = "https://tailscale.com/kb/1080/cli#up"
#: How often to poll the mesh challenge endpoint while waiting for authorization.
POLL_INTERVAL_SECONDS = 1
#: How long to let a single ``tailscale`` invocation (``up`` / ``cert`` /
#: ``logout``) run before treating it as wedged. Generous: a real enrollment does
#: a network round-trip to the coord server. A hung ``tailscaled`` would
#: otherwise block the CLI indefinitely.
TAILSCALE_UP_TIMEOUT_SECONDS = 90
#: Machine-global state dir for the userspace proxy daemon (`mesh proxy`).
TAILSCALED_STATE_DIR = Path.home() / ".arkitekt" / "mesh"
#: Default local address the `mesh proxy` HTTP proxy listens on.
DEFAULT_PROXY_LISTEN = "localhost:1055"
#: Locations to look for the `tailscaled` daemon (often off a non-root PATH).
TAILSCALED_FALLBACK_PATHS = (
    "/usr/sbin/tailscaled",
    "/usr/local/bin/tailscaled",
    "/usr/local/sbin/tailscaled",
)


async def _fetch_well_known(url: str) -> Dict[str, Any]:
    """Fetch and parse the ``/.well-known/fakts`` document for ``url``.

    Returns the raw JSON dict (not a pydantic model) so extra fields such as the
    ``mesh_*`` endpoints -- which are not part of the ``fakts`` models --
    survive. Mirrors the connection handling of
    ``fakts.grants.remote.discovery.utils.check_wellknown``.
    """
    import aiohttp

    # Auto-protocol: if the user did not specify a scheme, try https then http.
    if "://" in url:
        candidates = [url]
    else:
        candidates = [f"https://{url}", f"http://{url}"]

    last_error: Optional[Exception] = None
    async with aiohttp.ClientSession(
        headers={"User-Agent": "Fakts/0.1", "Accept": "application/json"},
    ) as session:
        for base in candidates:
            well_known = f"{base.rstrip('/')}/.well-known/fakts"
            try:
                async with session.get(
                    well_known,
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as resp:
                    if resp.status != 200:
                        last_error = RuntimeError(
                            f"{well_known} answered with status {resp.status}"
                        )
                        continue
                    try:
                        # content_type=None: accept JSON even if the server does
                        # not set a precise application/json content-type.
                        return await resp.json(content_type=None)
                    except Exception as e:  # not valid JSON
                        last_error = e
                        continue
            except Exception as e:  # connection error, DNS, timeout, ...
                last_error = e
                continue

    cli_error(
        f"Could not read the well-known Fakts document from '{url}'. "
        f"Is a Fakts server running there? ({last_error})"
    )


def _extract_mesh_endpoints(data: Dict[str, Any], url: str) -> Dict[str, Optional[str]]:
    """Pull the mesh device-code endpoints out of a well-known document.

    Raises if the deployment does not advertise the required start/challenge
    endpoints (i.e. it does not support the mesh device-code flow).
    """
    start_url = data.get("mesh_device_code_start")
    challenge_url = data.get("mesh_challenge_url")
    if not start_url or not challenge_url:
        cli_error(
            f"The Fakts server at '{url}' does not support the mesh device-code flow "
            f"(its well-known document is missing 'mesh_device_code_start' / "
            f"'mesh_challenge_url'). This deployment cannot enroll machines this way."
        )
    return {
        "start_url": start_url,
        "challenge_url": challenge_url,
        "configure_url": data.get("mesh_configure"),
        "coord_url": data.get("mesh_coord_url"),
    }


async def _mesh_start(start_url: str, payload: Dict[str, Any]) -> Tuple[str, str]:
    """Start a mesh device-code flow; returns ``(code, challenge)``.

    ``code`` identifies the request on the web authorization page; ``challenge``
    is the secret used to poll for the result. They are deliberately distinct.
    """
    import aiohttp

    async with aiohttp.ClientSession() as session:
        async with session.post(
            start_url, json=payload, timeout=aiohttp.ClientTimeout(total=10)
        ) as resp:
            if resp.status != 200:
                body = await resp.text()
                cli_error(
                    f"Could not start the mesh device-code flow at {start_url} "
                    f"(status {resp.status}). {body[:200]}"
                )
            result = await resp.json(content_type=None)

    if result.get("status") != "granted":
        cli_error(
            "The Fakts server refused to start a mesh join: "
            f"{result.get('error', 'unknown error')}."
        )
    return result["code"], result["challenge"]


async def _mesh_poll(challenge_url: str, challenge: str, timeout: int) -> Dict[str, Any]:
    """Poll the mesh challenge endpoint until it is granted, denied, or times out.

    Returns the granted payload (``ionscale_auth_key`` / ``ionscale_coord_url`` /
    ``machine_name``).
    """
    import aiohttp

    start_time = time.monotonic()
    async with aiohttp.ClientSession() as session:
        while True:
            async with session.post(
                challenge_url,
                json={"code": challenge},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    cli_error(
                        f"Could not poll the mesh challenge at {challenge_url} "
                        f"(status {resp.status}). {body[:200]}"
                    )
                result = await resp.json(content_type=None)

            status = result.get("status")
            if status == "granted":
                return result
            if status in ("pending", "waiting"):
                if time.monotonic() - start_time > timeout:
                    cli_error(
                        f"The mesh join was not authorized within {timeout} seconds. "
                        f"Ask an organization member to approve it, or retry with a "
                        f"longer --expiration."
                    )
                await asyncio.sleep(POLL_INTERVAL_SECONDS)
                continue
            if status == "denied":
                cli_error(
                    "The mesh join request was denied by the authorizer."
                )
            if status == "expired":
                cli_error(
                    "The mesh join request expired before it was authorized."
                )
            if status == "error":
                cli_error(
                    "The mesh challenge reported an error: "
                    f"{result.get('error', 'unknown error')}."
                )
            cli_error(f"Unexpected mesh challenge status: {status!r}.")


def _build_configure_url(base: Optional[str], code: str) -> Optional[str]:
    """Build the web authorization URL for ``code`` from the advertised base."""
    if not base:
        return None
    if "<code>" in base:
        return base.replace("<code>", code)
    if "{code}" in base:
        return base.replace("{code}", code)
    return f"{base.rstrip('/')}/{code}"


def _display_configure_prompt(
    console, configure_url: Optional[str], code: str, open_browser: bool
) -> None:
    """Show the user where to authorize the join (and open a browser if asked)."""
    if configure_url:
        if open_browser:
            try:
                webbrowser.open_new(configure_url)
            except Exception:
                pass  # headless boxes have no browser; the printed URL is enough
        console.print(
            Panel.fit(
                "An organization member must authorize this machine to join the mesh.\n"
                "Open the following page and approve the request:\n"
                f"[bold green][link={configure_url}]{configure_url}[/link][/bold green]\n\n"
                f"Join code: [bold blue]{code}[/bold blue]",
                title="Mesh Join Authorization",
                title_align="center",
            )
        )
    else:
        console.print(
            f"Ask an organization member to authorize mesh join code "
            f"[bold blue]{code}[/bold blue] on the Fakts server."
        )


def _run_mesh_device_code(
    console,
    endpoints: Dict[str, Optional[str]],
    payload: Dict[str, Any],
    open_browser: bool,
    timeout: int,
) -> Dict[str, Any]:
    """Drive the full device-code flow: start -> show URL -> poll -> granted."""
    # start_url/challenge_url are guaranteed non-None by _extract_mesh_endpoints.
    start_url = str(endpoints["start_url"])
    challenge_url = str(endpoints["challenge_url"])

    code, challenge = asyncio.run(_mesh_start(start_url, payload))
    configure_url = _build_configure_url(endpoints.get("configure_url"), code)
    _display_configure_prompt(console, configure_url, code, open_browser)

    with console.status("Waiting for an organization member to authorize this machine..."):
        return asyncio.run(_mesh_poll(challenge_url, challenge, timeout))


def _ensure_tailscale_installed(console) -> None:
    """Abort with install guidance if the ``tailscale`` binary is not on PATH."""
    if shutil.which("tailscale") is not None:
        return

    console.print(
        "[bold red]tailscale is not installed[/bold red] (or not on your PATH).",
    )
    console.print(
        f"Install it from [link={TAILSCALE_INSTALL_URL}]{TAILSCALE_INSTALL_URL}[/link] "
        "— on Linux you can run:"
    )
    console.print("    curl -fsSL https://tailscale.com/install.sh | sh", style="cyan")
    cli_error(
        "tailscale is required for the `mesh` commands. See "
        f"{TAILSCALE_INSTALL_URL} to install it."
    )


def _redact(args: List[str]) -> List[str]:
    """Redact secret-bearing args (e.g. ``--authkey=…``) for display."""
    redacted = []
    for arg in args:
        if arg.startswith("--authkey="):
            redacted.append("--authkey=***")
        else:
            redacted.append(arg)
    return redacted


def _run_tailscale(console, args: List[str]) -> None:
    """Run ``tailscale <args>``, retrying with ``sudo`` if it exits non-zero.

    Output is streamed (not captured) so tailscale's progress stays visible. The
    printed command line redacts secrets like the pre-auth key.
    """
    _ensure_tailscale_installed(console)
    command = ["tailscale", *args]
    console.print(f"Running: {' '.join(_redact(command))}", style="cyan")
    try:
        result = subprocess.run(command, timeout=TAILSCALE_UP_TIMEOUT_SECONDS)
    except FileNotFoundError:
        cli_error(
            "Could not find the 'tailscale' binary. Please install tailscale first "
            f"(see {TAILSCALE_INSTALL_URL})."
        )
    except subprocess.TimeoutExpired:
        cli_error(
            f"'{' '.join(_redact(command))}' did not finish within "
            f"{TAILSCALE_UP_TIMEOUT_SECONDS}s and was aborted. Check `tailscale status` "
            "and that tailscaled is healthy."
        )

    if result.returncode == 0:
        return

    # Most tailscale operations need root; retry once with sudo.
    sudo_command = ["sudo", *command]
    console.print(
        f"'{' '.join(_redact(command))}' exited with {result.returncode}, "
        f"retrying with sudo...",
        style="yellow",
    )
    console.print(f"Running: {' '.join(_redact(sudo_command))}", style="cyan")
    try:
        sudo_result = subprocess.run(sudo_command, timeout=TAILSCALE_UP_TIMEOUT_SECONDS)
    except FileNotFoundError:
        cli_error(
            "Could not find the 'sudo' binary to retry with elevated privileges."
        )
    except subprocess.TimeoutExpired:
        cli_error(
            f"'{' '.join(_redact(sudo_command))}' did not finish within "
            f"{TAILSCALE_UP_TIMEOUT_SECONDS}s and was aborted. Check `tailscale status` "
            "and that tailscaled is healthy."
        )

    if sudo_result.returncode != 0:
        cli_error(
            f"'{' '.join(_redact(sudo_command))}' failed "
            f"(exit code {sudo_result.returncode})."
        )


def _find_tailscaled() -> Optional[str]:
    """Locate the ``tailscaled`` daemon binary (it is often off a non-root PATH)."""
    found = shutil.which("tailscaled")
    if found:
        return found
    for candidate in TAILSCALED_FALLBACK_PATHS:
        if Path(candidate).exists():
            return candidate
    return None


def _ensure_tailscaled_installed(console) -> str:
    """Return the ``tailscaled`` path or abort with install guidance."""
    path = _find_tailscaled()
    if path:
        return path
    console.print(
        "[bold red]tailscaled is not installed[/bold red] (or not found).",
    )
    console.print(
        f"Install tailscale from "
        f"[link={TAILSCALE_INSTALL_URL}]{TAILSCALE_INSTALL_URL}[/link] — the "
        "`tailscaled` daemon is required for `mesh proxy`."
    )
    cli_error(
        f"tailscaled is required for `mesh proxy`. See {TAILSCALE_INSTALL_URL}."
    )


def _userspace_daemon_command(
    tailscaled_path: str,
    http_listen: str,
    socks5_listen: Optional[str],
    state_dir: Path,
) -> List[str]:
    """Build the userspace-networking ``tailscaled`` command exposing an HTTP proxy."""
    command = [
        tailscaled_path,
        "--tun=userspace-networking",
        f"--statedir={state_dir}",
        f"--socket={state_dir / 'tailscaled.sock'}",
        f"--outbound-http-proxy-listen={http_listen}",
    ]
    if socks5_listen:
        command.append(f"--socks5-server={socks5_listen}")
    return command


def _bring_up_via_socket(
    console,
    socket_path: Path,
    up_args: List[str],
    attempts: int = 40,
    delay: float = 0.5,
) -> None:
    """Run ``tailscale --socket=… up …`` against a just-started userspace daemon.

    The daemon needs a moment to create its socket, so this retries until the
    command succeeds (or the attempts budget is exhausted).
    """
    command = ["tailscale", f"--socket={socket_path}", *up_args]
    console.print(f"Running: {' '.join(_redact(command))}", style="cyan")
    last: Optional[subprocess.CompletedProcess] = None
    timed_out = False
    for _ in range(attempts):
        try:
            last = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=TAILSCALE_UP_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired:
            # A wedged bring-up shouldn't hang the CLI; stop retrying and report.
            timed_out = True
            break
        if last.returncode == 0:
            return
        time.sleep(delay)
    if timed_out:
        cli_error(
            f"`tailscale up` did not finish within {TAILSCALE_UP_TIMEOUT_SECONDS}s "
            "and was aborted. The userspace tailscaled may be wedged."
        )
    detail = (last.stderr or last.stdout or "").strip() if last else ""
    cli_error(
        "Could not bring the mesh proxy up "
        f"(`tailscale up` kept failing). {detail[:200]}"
    )


mesh = typer.Typer(
    no_args_is_help=True,
    help="""Join this machine to the Arkitekt WireGuard mesh via tailscale.

    An Arkitekt deployment can front its services with a private WireGuard mesh
    (an ionscale tailnet). Use `mesh join` to enroll this machine (an org member
    authorizes it on a web page and it receives a single-use pre-auth key),
    `mesh leave` to disconnect and deregister it, `mesh proxy` to join and expose
    a local HTTP proxy into the mesh, and `mesh cert` to fetch a TLS certificate.

    These commands drive the local `tailscale` binary (falling back to `sudo` when
    elevated privileges are required), so tailscale must be installed first --
    see https://tailscale.com/download.
    """,
)


def _device_code_join(
    console,
    url: str,
    machine_name: Optional[str],
    description: Optional[str],
    ephemeral: bool,
    tags: Tuple[str, ...],
    expiration: int,
    open_browser: bool,
) -> Tuple[str, str, str]:
    """Run the mesh device-code flow; returns ``(authkey, coord_url, hostname)``."""
    machine_name = machine_name or socket.gethostname()

    console.print(f"Inspecting well-known Fakts at [cyan]{url}[/cyan]...")
    data = asyncio.run(_fetch_well_known(url))
    endpoints = _extract_mesh_endpoints(data, url)

    payload = {
        "requested_machine_name": machine_name,
        "description": description,
        "ephemeral": ephemeral,
        "tags": list(tags),
        "expiration_time_seconds": expiration,
    }

    granted = _run_mesh_device_code(console, endpoints, payload, open_browser, expiration)

    key = granted.get("ionscale_auth_key")
    if not key:
        cli_error(
            "The mesh server authorized the join but returned no auth key."
        )
    coord = granted.get("ionscale_coord_url") or endpoints.get("coord_url")
    if not coord:
        cli_error(
            "The mesh server authorized the join but returned no coordination URL."
        )
    hostname = granted.get("machine_name") or machine_name
    return key, coord, hostname


def join(
    ctx: typer.Context,
    url: UrlOption = DEFAULT_ARKITEKT_URL,
    machine_name: Annotated[
        Optional[str],
        typer.Option(
            "--name",
            "-n",
            help="Requested machine name (a hint; defaults to this host's hostname). "
            "The authorizer may edit it.",
        ),
    ] = None,
    description: Annotated[
        Optional[str],
        typer.Option(
            "--description",
            help="Human-readable purpose, shown on the authorization page.",
        ),
    ] = None,
    ephemeral: Annotated[
        bool,
        typer.Option(
            "--ephemeral",
            help="Request an ephemeral node (advisory; the authorizer decides the key type).",
        ),
    ] = False,
    tags: Annotated[
        List[str],
        typer.Option(
            "--tag",
            help="Requested ionscale ACL tag (repeatable; advisory).",
        ),
    ] = [],
    expiration: Annotated[
        int,
        typer.Option(
            "--expiration",
            help="How long the join code stays valid, in seconds (default 600).",
        ),
    ] = 600,
    open_browser: Annotated[
        bool,
        typer.Option(
            "--open-browser/--no-open-browser",
            help="Open the authorization page in a browser (default: open).",
        ),
    ] = True,
) -> None:
    """Join the mesh via the device-code flow (a human authorizes this machine).

    Discovers the mesh device-code endpoints from the Fakts server's well-known
    document, requests a join code, shows the authorization page for an
    organization member to approve, then polls for a single-use pre-auth key and
    runs `tailscale up --authkey=… --hostname=… --login-server=… --force-reauth`.

    See the tailscale `up` reference for the underlying behaviour:
    https://tailscale.com/kb/1080/cli#up
    """
    console = get_console(ctx)

    # Fail fast (before the network lookup) if tailscale is missing.
    _ensure_tailscale_installed(console)

    key, coord, hostname = _device_code_join(
        console, url, machine_name, description, ephemeral, tags, expiration, open_browser
    )

    console.print(f"Authorized as [green]{hostname}[/green]; joining the mesh...")
    _run_tailscale(
        console,
        [
            "up",
            f"--login-server={coord}",
            f"--authkey={key}",
            f"--hostname={hostname}",
            "--force-reauth",
        ],
    )


def leave(
    ctx: typer.Context,
    yes: Annotated[
        bool,
        typer.Option("--yes", "-y", help="Skip the confirmation prompt."),
    ] = False,
) -> None:
    """Leave the mesh: disconnect and deregister this node (`tailscale logout`).

    This logs the node out of the tailnet, so a fresh `mesh join` (with a new
    authorization) is needed to reconnect.
    """
    console = get_console(ctx)
    _ensure_tailscale_installed(console)

    if not yes:
        require_interactive("Confirming the mesh logout", hint="Pass --yes to leave non-interactively.")
        console.print(
            "[bold yellow]Warning:[/bold yellow] this deregisters the node from the "
            "mesh; reconnecting requires a fresh `mesh join` authorization."
        )
        confirm_or_abort("Log out of the mesh?")

    _run_tailscale(console, ["logout"])


def proxy(
    ctx: typer.Context,
    url: Annotated[
        str,
        typer.Option(
            "--url",
            "-u",
            help="The fakts url for connection",
            envvar="FAKTS_URL",
        ),
    ] = DEFAULT_ARKITEKT_URL,
    machine_name: Annotated[
        Optional[str],
        typer.Option(
            "--name",
            "-n",
            help="Requested machine name (a hint; defaults to this host's hostname). "
            "The authorizer may edit it.",
        ),
    ] = None,
    description: Annotated[
        Optional[str],
        typer.Option(
            "--description",
            help="Human-readable purpose, shown on the authorization page.",
        ),
    ] = None,
    ephemeral: Annotated[
        bool,
        typer.Option(
            "--ephemeral",
            help="Request an ephemeral node (advisory; the authorizer decides the key type).",
        ),
    ] = False,
    tags: Annotated[
        List[str],
        typer.Option(
            "--tag",
            help="Requested ionscale ACL tag (repeatable; advisory).",
        ),
    ] = [],
    expiration: Annotated[
        int,
        typer.Option(
            "--expiration",
            help="How long the join code stays valid, in seconds (default 600).",
        ),
    ] = 600,
    open_browser: Annotated[
        bool,
        typer.Option(
            "--open-browser/--no-open-browser",
            help="Open the authorization page in a browser (default: open).",
        ),
    ] = True,
    listen: Annotated[
        str,
        typer.Option(
            "--listen",
            help=f"Local HTTP proxy listen address (default {DEFAULT_PROXY_LISTEN}).",
        ),
    ] = DEFAULT_PROXY_LISTEN,
    socks5_listen: Annotated[
        Optional[str],
        typer.Option(
            "--socks5-listen",
            help="Also expose a SOCKS5 proxy on this address (e.g. localhost:1080).",
        ),
    ] = None,
) -> None:
    """Join the mesh and run a local HTTP proxy into it (userspace networking).

    Runs the device-code join to obtain a pre-auth key, then starts `tailscaled`
    in userspace-networking mode exposing an outbound HTTP proxy (and optionally a
    SOCKS5 proxy). Point other processes at it with `HTTP_PROXY=http://<listen>`
    to reach mesh services without a TUN device or root. Runs in the foreground;
    press Ctrl-C to stop.
    """
    console = get_console(ctx)

    # Fail fast: both the CLI and the daemon must be present.
    _ensure_tailscale_installed(console)
    tailscaled_path = _ensure_tailscaled_installed(console)

    key, coord, hostname = _device_code_join(
        console, url, machine_name, description, ephemeral, tags, expiration, open_browser
    )

    TAILSCALED_STATE_DIR.mkdir(parents=True, exist_ok=True)
    socket_path = TAILSCALED_STATE_DIR / "tailscaled.sock"
    daemon_command = _userspace_daemon_command(
        tailscaled_path, listen, socks5_listen, TAILSCALED_STATE_DIR
    )

    console.print(f"Running: {' '.join(daemon_command)}", style="cyan")
    try:
        proc = subprocess.Popen(daemon_command)
    except FileNotFoundError:
        cli_error(
            f"Could not launch 'tailscaled' at {tailscaled_path}."
        )

    try:
        _bring_up_via_socket(
            console,
            socket_path,
            [
                "up",
                f"--login-server={coord}",
                f"--authkey={key}",
                f"--hostname={hostname}",
                "--force-reauth",
            ],
        )

        proxy_lines = f"HTTP proxy: [green]http://{listen}[/green]"
        if socks5_listen:
            proxy_lines += f"\nSOCKS5 proxy: [green]socks5://{socks5_listen}[/green]"
        console.print(
            Panel.fit(
                f"Joined the mesh as [green]{hostname}[/green].\n\n"
                f"{proxy_lines}\n\n"
                "Set HTTP_PROXY / HTTPS_PROXY (or ALL_PROXY) to route into the mesh.\n"
                "Press Ctrl-C to stop.",
                title="Mesh Proxy",
                title_align="center",
            )
        )
        proc.wait()
    except KeyboardInterrupt:
        console.print("\nStopping mesh proxy...", style="yellow")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


def cert(
    ctx: typer.Context,
    domain: Annotated[Optional[str], typer.Argument()] = None,
) -> None:
    """Fetch a TLS certificate for this node via `tailscale cert`.

    With no DOMAIN, tailscale issues a certificate for this node's own MagicDNS
    name. Pass an explicit DOMAIN to request a certificate for that name instead.
    Requires the machine to already be joined to the mesh (see `mesh join`).
    """
    console = get_console(ctx)
    _ensure_tailscale_installed(console)
    args = ["cert"]
    if domain:
        args.append(domain)
    _run_tailscale(console, args)


mesh.command("join")(join)
mesh.command("leave")(leave)
mesh.command("proxy")(proxy)
mesh.command("cert")(cert)
