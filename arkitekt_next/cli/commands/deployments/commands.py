"""Generic lifecycle commands, built once per deployment kind.

Every deployment kind (`hub`, `coord`, `hubinator`, `engine`) gets the same
`up`/`down`/`logs`/`status` commands. They differ only by a lookup in
``server.deployments.DEPLOYMENTS``, so each is produced by a factory here rather
than hand-written four times.

All four go through :mod:`arkitekt_next.server.lifecycle`, so the CLI and the test
fixtures drive docker through the same dokker deployment object.
"""

import time
from typing import Annotated, Callable, List, Optional  # noqa: F401

import typer

from arkitekt_next.cli.errors import cli_error
from arkitekt_next.cli.vars import get_console
from arkitekt_next.cli.commands._server_common import resolve_path

#: `status` must answer quickly, so it probes once with a short timeout rather than
#: using the patient first-boot retries that `up`/tests want.
STATUS_TIMEOUT = 5
STATUS_RETRIES = 1


def _require_docker() -> None:
    """Fail with a friendly message when docker is missing."""
    import shutil

    if not shutil.which("docker"):
        cli_error(
            "Docker is not installed, but it is required for this command.\n"
            "Install Docker (https://docs.docker.com/get-docker/) and try again."
        )


def _printer(ctx: typer.Context) -> Callable[[str], None]:
    """Route dokker's compose output through the CLI console, dimmed."""
    console = get_console(ctx)
    return lambda line: console.print(f"[dim]{line}[/dim]", highlight=False)


def _open(ctx: typer.Context, path: Optional[str], kind: str, **kwargs):
    """Resolve the deployment directory and open it, with friendly errors."""
    from arkitekt_next.server.lifecycle import open_deployment

    target = resolve_path(ctx, path)
    kwargs.setdefault("printer", _printer(ctx))
    try:
        return open_deployment(target, kind, **kwargs)
    except FileNotFoundError:
        cli_error(
            f"No deployment found at {target}. Run `{kind} init` and `{kind} up` first."
        )


def make_up_command(kind_name: str) -> Callable[..., None]:
    """Build the ``up`` command: regenerate the deployment files, then start it.

    Regenerating on every ``up`` is deliberate -- the profile YAML is the source of
    truth, so editing it and re-running ``up`` applies the change.
    """

    def up(
        ctx: typer.Context,
        path: Annotated[Optional[str], typer.Argument()] = None,
        wait: Annotated[
            bool,
            typer.Option("--wait", help="Wait until every service reports healthy."),
        ] = False,
    ) -> None:
        """Compose the deployment (services + auth wiring) and start it."""
        from arkitekt_next.server.deployments import DEPLOYMENTS
        from arkitekt_next.server.lifecycle import load_config, open_deployment

        spec = DEPLOYMENTS[kind_name]
        console = get_console(ctx)
        target = resolve_path(ctx, path)

        try:
            config = load_config(target, kind_name)
        except FileNotFoundError:
            cli_error(
                f"No configuration found at {target / spec.filename}. "
                f"Run `{kind_name} init` first."
            )

        console.print("[blue]Composing deployment (services + auth wiring)...[/blue]")
        spec.generator(target, config)

        # Generation already succeeded, so if docker is missing we can point the user
        # at ready-to-run files rather than failing opaquely.
        import shutil

        if not shutil.which("docker"):
            cli_error(
                "Docker is not installed, but it is required to start the stack with `up`.\n"
                f"The deployment files were generated in {target} — install Docker "
                "(https://docs.docker.com/get-docker/) and run `docker compose up` there."
            )

        deployment, config = open_deployment(
            target,
            kind_name,
            config=config,
            with_health=wait,
            printer=_printer(ctx),
        )
        console.print("[blue]Starting the stack...[/blue]")
        try:
            # dokker's sync API needs an active koil context. The `manual` teardown
            # policy means leaving this block does NOT stop what we just started.
            with deployment:
                deployment.up()
                if wait:
                    console.print(
                        "[blue]Waiting for services to become healthy...[/blue]"
                    )
                    deployment.check_health()
        except Exception as e:  # pragma: no cover - surfaced to the user
            cli_error(f"Failed to start the stack (is Docker running?): {e}")

        console.print("[bold green]✓ Deployment is up.[/bold green]")
        if not wait and spec.bootable:
            console.print(f"[dim]Check it with `{kind_name} status`.[/dim]")

    return up


def make_down_command(kind_name: str) -> Callable[..., None]:
    """Build the ``down`` command: stop and remove the deployment's containers."""

    def down(
        ctx: typer.Context,
        path: Annotated[Optional[str], typer.Argument()] = None,
        volumes: Annotated[
            bool,
            typer.Option(
                "--volumes",
                help="Also remove named volumes — DELETES the database and object store.",
            ),
        ] = False,
    ) -> None:
        """Stop the deployment and remove its containers."""
        _require_docker()
        console = get_console(ctx)
        deployment, _config = _open(ctx, path, kind_name, with_health=False)

        # dokker's `local` policy keeps volumes by default, which is what a real
        # server wants; --volumes is the explicit, destructive opt-in.
        deployment.remove_volumes_on_down = volumes
        if volumes:
            console.print("[yellow]Removing volumes — stored data will be lost.[/yellow]")

        console.print("[blue]Stopping the deployment...[/blue]")
        try:
            with deployment:
                deployment.down()
        except Exception as e:  # pragma: no cover - surfaced to the user
            cli_error(f"Failed to stop the stack: {e}")
        console.print("[bold green]✓ Deployment is down.[/bold green]")

    return down


def make_logs_command(kind_name: str) -> Callable[..., None]:
    """Build the ``logs`` command: stream (or dump) service logs."""

    def logs(
        ctx: typer.Context,
        services: Annotated[
            Optional[List[str]],
            typer.Argument(help="Services to show logs for. Defaults to all of them."),
        ] = None,
        path: Annotated[
            Optional[str],
            typer.Option("--path", help="Deployment directory. Defaults to --work-dir."),
        ] = None,
        follow: Annotated[
            bool,
            typer.Option("--follow/--no-follow", "-f", help="Keep streaming new logs."),
        ] = True,
        tail: Annotated[
            Optional[int],
            typer.Option("--tail", "-n", help="Only show the last N lines per service."),
        ] = None,
    ) -> None:
        """Show logs from the deployment's services."""
        _require_docker()
        console = get_console(ctx)
        deployment, _config = _open(ctx, path, kind_name, with_health=False, verbose=False)

        watcher = deployment.create_watcher(
            services=list(services) if services else [],
            follow=follow,
            tail=tail,
            wait_for_first_log=False,
            # Without --follow the log command terminates on its own; wait for it,
            # otherwise the block exits before any line has been read and nothing
            # is printed at all.
            wait_for_logs=not follow,
            append_to_traceback=False,
            capture_stdout=False,
            log_function=lambda log: console.print(log[1], highlight=False),
        )

        try:
            # The watcher streams through the deployment's CLI, so it needs the
            # deployment's koil context to be active.
            with deployment, watcher:
                if follow:
                    console.print("[dim]Streaming logs — press Ctrl-C to stop.[/dim]")
                    while True:
                        time.sleep(0.5)
        except KeyboardInterrupt:  # pragma: no cover - interactive
            console.print("\n[dim]Stopped streaming.[/dim]")
        except Exception as e:  # pragma: no cover - surfaced to the user
            cli_error(f"Failed to read logs: {e}")

    return logs


def make_status_command(kind_name: str) -> Callable[..., None]:
    """Build the ``status`` command: show services, ports and health."""

    def status(
        ctx: typer.Context,
        path: Annotated[Optional[str], typer.Argument()] = None,
    ) -> None:
        """Show the deployment's services, published ports and health."""
        from rich.table import Table

        from arkitekt_next.server.lifecycle import (
            GATEWAY_INTERNAL_PORT,
            health_services,
            register_health_checks,
        )

        _require_docker()
        console = get_console(ctx)
        deployment, config = _open(ctx, path, kind_name, with_health=False, verbose=False)

        # ``inspect`` is sync-over-async and needs the koil context. Reading
        # ``spec`` afterwards does not, so the context can close straight away.
        try:
            with deployment:
                deployment.inspect()
        except Exception as e:
            cli_error(f"Could not inspect the deployment (is it up?): {e}")

        spec = deployment.spec
        gateway = spec.find_service("gateway")
        if gateway is not None:
            port = gateway.get_port_for_internal(GATEWAY_INTERNAL_PORT)
            if port is not None:
                console.print(f"Gateway: [cyan]http://localhost:{port.published}[/cyan]\n")

        services = health_services(config)
        if not services:
            # Engine has no gateway and no web services -- report the containers only.
            console.print(
                f"[dim]{kind_name} deploys no gateway-routed web services; "
                "showing containers only.[/dim]"
            )
            table = Table(title=f"{kind_name} containers")
            table.add_column("Service", style="cyan")
            for name in (spec.services or {}):
                table.add_row(name)
            console.print(table)
            return

        # Probe once with a short timeout: `status` should answer now, not retry
        # patiently the way a first boot does.
        register_health_checks(
            deployment, config, timeout=STATUS_TIMEOUT, max_retries=STATUS_RETRIES
        )

        # Probe every service concurrently. The sync ``check_health()`` takes no
        # arguments and raises on the first failure, which would hide the rest --
        # so each check is awaited individually and its outcome recorded.
        import asyncio

        async def probe(check) -> bool:
            try:
                await check.acheck(spec)
                return True
            except Exception:
                return False

        async def probe_all() -> list[bool]:
            return list(
                await asyncio.gather(*(probe(c) for c in deployment.health_checks))
            )

        outcomes = asyncio.run(probe_all())

        table = Table(title=f"{kind_name} services")
        table.add_column("Service", style="cyan")
        table.add_column("Health")
        table.add_column("URL", style="dim")

        healthy = 0
        for check, ok in zip(deployment.health_checks, outcomes):
            if ok:
                healthy += 1
            state = "[green]healthy[/green]" if ok else "[red]unhealthy[/red]"
            url = check.url(spec) if callable(check.url) else check.url
            table.add_row(check.service, state, url)

        console.print(table)
        total = len(deployment.health_checks)
        if healthy == total:
            console.print(f"[bold green]✓ All {total} service(s) healthy.[/bold green]")
        else:
            console.print(
                f"[yellow]{healthy}/{total} service(s) healthy. "
                f"Inspect a failing one with `{kind_name} logs <service>`.[/yellow]"
            )

    return status
