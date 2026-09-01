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
from arkitekt_next.server.kinds import KINDS, KindMeta
from arkitekt_next.server import wizard


@dataclass(frozen=True)
class DeploymentKind:
    """Everything the generic lifecycle flow needs to drive one deployment kind.

    The static half (name, filename, help, ``supports_services``, ``bootable``) comes
    from :data:`arkitekt_next.server.kinds.KINDS` and is exposed here by delegation,
    so there is exactly one place describing a kind. This class adds only the heavy
    bindings that require the ``server`` extra: config class, generator, wizard.

    ``wizard`` is ``None`` for kinds without an interactive wizard (``engine``).
    """

    meta: KindMeta
    config_cls: Type[BaseModel]
    generator: Callable[[Path, Any], None]
    wizard: Optional[Callable[..., BaseModel]] = None

    @property
    def name(self) -> str:
        """CLI group name and on-disk profile ``kind`` marker."""
        return self.meta.name

    @property
    def filename(self) -> str:
        """Profile YAML filename inside the deployment directory."""
        return self.meta.filename

    @property
    def supports_services(self) -> bool:
        """Whether this kind carries selectable data/compute services."""
        return self.meta.supports_services

    @property
    def bootable(self) -> bool:
        """Whether this kind can be started and health-checked on its own."""
        return self.meta.bootable

    @property
    def help(self) -> str:
        """Help text for the CLI group."""
        return self.meta.help


DEPLOYMENTS: dict[str, DeploymentKind] = {
    "hub": DeploymentKind(
        meta=KINDS["hub"],
        config_cls=HubConfig,
        generator=write_hub_files,
        wizard=wizard.prompt_hub_config,
    ),
    "coord": DeploymentKind(
        meta=KINDS["coord"],
        config_cls=CoordConfig,
        generator=write_coord_files,
        wizard=wizard.prompt_coord_config,
    ),
    "hubinator": DeploymentKind(
        meta=KINDS["hubinator"],
        config_cls=ArkitektServerConfig,
        generator=write_virtual_config_files,
        wizard=wizard.prompt_config,
    ),
    "engine": DeploymentKind(
        meta=KINDS["engine"],
        config_cls=EngineConfig,
        generator=write_engine_files,
        wizard=None,
    ),
}
