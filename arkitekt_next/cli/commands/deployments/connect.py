"""``arkitekt-next hub connect`` -- register a hub's services with an organization."""

from typing import Annotated, Optional

import typer
from rich.table import Table

from arkitekt_next.cli.errors import cli_error
from arkitekt_next.cli.vars import get_console
from arkitekt_next.cli.commands._server_common import resolve_path


def connect(
    ctx: typer.Context,
    path: Annotated[Optional[str], typer.Argument()] = None,
    server: Annotated[
        Optional[str],
        typer.Option(
            "--server",
            help="Organization coordination (Lok) server to connect to. Defaults to the hub's coord_server.",
        ),
    ] = None,
    no_browser: Annotated[
        bool,
        typer.Option("--no-browser", help="Do not open the authorization page in a browser."),
    ] = False,
    timeout: Annotated[
        float,
        typer.Option("--timeout", help="Seconds to wait for authorization."),
    ] = 120.0,
    no_resolve: Annotated[
        bool,
        typer.Option("--no-resolve", help="Do not reverse-resolve DNS host names for discovered IPs."),
    ] = False,
    resolve_timeout: Annotated[
        float,
        typer.Option(
            "--resolve-timeout",
            help="Seconds to wait for each reverse-DNS lookup before giving up on it.",
        ),
    ] = 2.0,
    all_hosts: Annotated[
        bool,
        typer.Option(
            "--all-hosts",
            "-a",
            help="Advertise every discovered host without prompting for a selection.",
        ),
    ] = False,
) -> None:
    """Connect this hub to an organization.

    Inspects the machine's current host addresses, builds a hub advertising each
    enabled hub service on those hosts, POSTs it to the organization's
    coordination server, and opens the browser to authorize it.
    """
    import asyncio
    import sys

    from arkitekt_next.server.config import HubConfig
    from arkitekt_next.server.connect import (
        build_hub,
        discover_host_candidates,
        register_hub,
    )
    from arkitekt_next.server.deployments import DEPLOYMENTS
    from arkitekt_next.server.utils import load_profile_yaml

    console = get_console(ctx)
    target = resolve_path(ctx, path)
    config_path = target / DEPLOYMENTS["hub"].filename

    try:
        config, _backend = load_profile_yaml(str(config_path), HubConfig)
    except FileNotFoundError:
        cli_error(
            f"No hub configuration found at {config_path}. Run `hub init` first."
        )

    server = server or config.coord_server

    console.print("[blue]Inspecting current hosts...[/blue]")
    candidates = discover_host_candidates(
        resolve_names=not no_resolve, resolve_timeout=resolve_timeout
    )
    if not candidates:
        cli_error(
            "Could not discover any routable host addresses to advertise."
        )

    table = Table(title="Discovered hosts")
    table.add_column("Host / IP", style="cyan", no_wrap=True)
    table.add_column("Kind", style="magenta")
    table.add_column("Details", style="dim")
    for cand in candidates:
        table.add_row(cand.value, cand.kind, cand.description)
    console.print(table)

    # Let the operator prune the advertised set -- addresses (docker/VPN) or
    # reverse-DNS names that other machines can't actually reach only add noise.
    # IP candidates are pre-selected; reverse-DNS names start off so they must be
    # opted in. Skipped when non-interactive or when --all-hosts is passed.
    interactive = sys.stdin.isatty() and not all_hosts
    if interactive:
        import inquirer

        answer = inquirer.prompt(
            [
                inquirer.Checkbox(
                    "hosts",
                    message="Select the hosts to advertise (space to toggle, enter to confirm)",
                    choices=[(f"{c.value}  ({c.description})", c.value) for c in candidates],
                    default=[c.value for c in candidates if c.is_ip],
                )
            ]
        )
        if answer is None:
            raise typer.Abort()
        selected = set(answer.get("hosts", []))
        hosts = [c.value for c in candidates if c.value in selected]
    else:
        hosts = [c.value for c in candidates]

    if not hosts:
        cli_error("No hosts selected to advertise.")

    console.print(f"Advertising [bold]{len(hosts)}[/bold] host(s): [cyan]{', '.join(hosts)}[/cyan]")

    request = build_hub(config, hosts)
    if not request.hub.instances:
        cli_error(
            "No enabled services to advertise. Enable services in the hub config first."
        )

    console.print(
        f"Registering [bold]{len(request.hub.instances)}[/bold] service(s) "
        f"with [cyan]{server}[/cyan]..."
    )
    try:
        completed, configure_url = asyncio.run(
            register_hub(
                request,
                server=server,
                open_browser=not no_browser,
                timeout=timeout,
                on_status=lambda s: console.print(f"[dim]authorization {s}...[/dim]"),
            )
        )
    except Exception as e:  # pragma: no cover - surfaced to the user
        cli_error(f"Failed to register with {server}: {e}")

    console.print(f"Authorize this connection at: [link={configure_url}]{configure_url}[/link]")
    if completed:
        console.print("[bold green]✓ Hub connected to the organization.[/bold green]")
    else:
        console.print(
            "[yellow]Authorization not confirmed yet. Complete it in the browser; "
            "the hub will be connected once approved.[/yellow]"
        )
