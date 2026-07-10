"""Registry of server-deployment kinds — the single source of truth.

Each of the four deployment CLI groups (`hub`, `coord`, `hubinator`, `engine`)
couples the same five things: a name, an on-disk config filename, a pydantic config
class, a compose/config generator, and (optionally) an interactive wizard. That
coupling used to be spelled out redundantly across the four ``cli/commands/*/main.py``
modules, the ``*_CONFIG_FILENAME`` constants, and ``server/dev.py``. This module
bundles it once as :class:`DeploymentKind` values in :data:`DEPLOYMENTS`.

The registry holds *real* references (config classes, generators, wizards), so it
transitively imports the ``server`` extra (``cryptography`` via config, ``inquirer``
via wizard). It must therefore only ever be imported **inside command callbacks**,
never at the top level of an eagerly-imported CLI module — otherwise the base CLI
would require the ``server`` extra just to load. See ``cli/commands/_server_common.py``.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional, Type

from pydantic import BaseModel

from arkitekt_next.server.config import (
    ArkitektServerConfig,
    CoordConfig,
    EngineConfig,
    HubConfig,
)
from arkitekt_next.server.diff import (
    write_coord_files,
    write_engine_files,
    write_hub_files,
    write_virtual_config_files,
)
from arkitekt_next.server import wizard


@dataclass(frozen=True)
class DeploymentKind:
    """Everything the generic ``init``/``up`` flow needs to drive one deployment kind.

    ``name`` doubles as the CLI group name and the on-disk profile ``kind`` marker.
    ``wizard`` is ``None`` for kinds without an interactive wizard (``engine``).
    """

    name: str
    filename: str
    config_cls: Type[BaseModel]
    generator: Callable[[Path, Any], None]
    wizard: Optional[Callable[..., BaseModel]] = None
    supports_services: bool = False


DEPLOYMENTS: dict[str, DeploymentKind] = {
    "hub": DeploymentKind(
        name="hub",
        filename="hub_config.yaml",
        config_cls=HubConfig,
        generator=write_hub_files,
        wizard=wizard.prompt_hub_config,
        supports_services=True,
    ),
    "coord": DeploymentKind(
        name="coord",
        filename="coord_config.yaml",
        config_cls=CoordConfig,
        generator=write_coord_files,
        wizard=wizard.prompt_coord_config,
    ),
    "hubinator": DeploymentKind(
        name="hubinator",
        filename="hubinator_config.yaml",
        config_cls=ArkitektServerConfig,
        generator=write_virtual_config_files,
        wizard=wizard.prompt_config,
        supports_services=True,
    ),
    "engine": DeploymentKind(
        name="engine",
        filename="engine_config.yaml",
        config_cls=EngineConfig,
        generator=write_engine_files,
        wizard=None,
    ),
}
