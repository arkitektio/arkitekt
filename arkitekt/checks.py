"""Checking whether apps fit together: do their dependencies bind?

An app that declares a protocol directed at another app demands actions and
states of it. :func:`check_apps` compares each such demand with what the other
app declares, the way the server does when a task is assigned, without running
or connecting anything. :func:`acheck_running` asks the server itself, for apps
that are registered: it also covers what is served from somewhere else.
"""

import textwrap
from collections.abc import Iterable
from dataclasses import dataclass, replace
from typing import Any, Protocol

from arkitekt_spec.declare.demands import DemandFinding, check_demands

from arkitekt.app.app import App


class _Running(Protocol):
    """What is read of a running app here (an :class:`arkitekt.runtime.Runtime` is one).

    Said as a protocol, so that this module does not import the runtime that imports it.
    """

    @property
    def app(self) -> App[Any]: ...
    @property
    def clients(self) -> dict[str, Any]: ...
    @property
    def snapshot(self) -> Any | None: ...  # noqa: ANN401


class DependencyCheckError(ValueError):
    """Apps run together do not fit: one demands what another does not offer.

    Attributes:
        findings: The demands that are not met.
    """

    def __init__(self, findings: list[DemandFinding]) -> None:
        """Say every unmet demand, each at the line that declares it."""
        self.findings = findings
        lines = [textwrap.indent(str(finding), "  ") for finding in findings]
        super().__init__(
            "These apps do not fit together, and the server would refuse to assign "
            "the tasks that depend on it:\n" + "\n".join(lines)
        )


def check_apps(*apps: App[Any]) -> list[DemandFinding]:
    """Compare what each app demands of the others with what they declare.

    Nothing is connected, logged in to or run. A protocol directed at an app
    that is not among ``apps`` is a ``note``: it cannot be compared, and nothing
    says it is wrong.

    ::

        errors = [f for f in check_apps(robot_app, protocol_app) if f.level == "error"]

    Args:
        *apps: The apps to check against each other.

    Returns:
        The findings, each naming the app that declared the protocol
        (``consumer``); empty when every demand that could be compared is met.
    """
    registries = {app.identifier: app.registry for app in apps}
    findings: list[DemandFinding] = []
    for app in apps:
        others = {identifier: registry for identifier, registry in registries.items() if identifier != app.identifier}
        findings.extend(replace(finding, consumer=app.identifier) for finding in check_demands(app.registry, others))
    return findings


@dataclass(frozen=True)
class UnmetDependency:
    """A dependency the server would refuse to bind if the action were assigned now.

    Attributes:
        app: The identifier of the app whose action it is.
        action: The action (its interface) that has the dependency.
        dependency: The key of the dependency; one further down the tree is
            given with the way to it (``robot > grip > gripper``).
        reason: Why it is refused, as the server says it.
    """

    app: str
    action: str
    dependency: str
    reason: str

    def __str__(self) -> str:
        """The finding as it is printed."""
        return f"{self.app}: {self.action}: {self.dependency}: {self.reason}"


def _rekuest_of(runtime: _Running) -> Any | None:  # noqa: ANN401
    """The run's client that can ask rekuest for a dry run, if it has one."""
    return next((client for client in runtime.clients.values() if hasattr(client, "adependency_tree")), None)


async def acheck_running(runtimes: Iterable[_Running]) -> list[UnmetDependency]:
    """Ask the server whether every dependency of these running apps would bind now.

    For each action with dependencies, the server resolves them as an assign
    would, without assigning (its dry run). It binds among every agent registered
    with it, so a dependency served by an app running somewhere else is checked
    like one served here -- and one whose app is not connected is unmet.

    Args:
        runtimes: Runs that are started and registered (see :func:`arkitekt.providing`).
            One that is not served by rekuest is left out.

    Returns:
        What would be refused; empty when every assign would go through.
    """
    unmet: list[UnmetDependency] = []
    for runtime in runtimes:
        rekuest = _rekuest_of(runtime)
        if rekuest is None or runtime.snapshot is None:
            continue
        app = runtime.app.identifier
        for interface, implementation in runtime.snapshot.registry.implementations.items():
            if not implementation.dependencies:
                continue
            mine = await rekuest.amy_implementation_at(interface=interface)
            tree = await rekuest.adependency_tree(implementation=mine.id)
            found = len(unmet)
            for dependency in tree.dependencies:
                if dependency.unmet:
                    unmet.append(UnmetDependency(app, interface, dependency.key, dependency.unmet))
                for agent in dependency.mapped_agents:
                    for bound in agent.mapped_implementations:
                        unmet.extend(
                            UnmetDependency(app, interface, f"{dependency.key} > {bound.key} > {below.key}", below.unmet)
                            for below in bound.resolved_dependencies
                            if below.unmet
                        )
            if not tree.satisfied and len(unmet) == found:
                # Deeper than the two levels asked for: the server still says no.
                unmet.append(UnmetDependency(app, interface, "*", "a dependency further down the tree is unmet"))
    return unmet


__all__ = ["DemandFinding", "DependencyCheckError", "UnmetDependency", "acheck_running", "check_apps"]
