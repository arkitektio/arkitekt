"""Arkitekt server deployment library.

This subpackage was migrated from the standalone ``arkitekt-server`` package. It
holds the framework-agnostic logic for generating an Arkitekt deployment: the
configuration models (:mod:`~arkitekt_next.server.config`), the service registry
(:mod:`~arkitekt_next.server.services`) and the compose/config generator
(:mod:`~arkitekt_next.server.diff`).

The user-facing CLI groups (`hub`, `coord`, `hubinator`, `engine`) are generated
from the :data:`~arkitekt_next.server.kinds.KINDS` registry in
:mod:`arkitekt_next.cli.commands.deployments` and call into this subpackage.
"""

from .dev import create_server
from .config import ArkitektServerConfig, Setup

__all__ = ["create_server", "ArkitektServerConfig", "Setup"]
