"""Qt related modules.

This module contains Modules that are Qt related, and help to integrate
Arkitekt with Qt applications.

The main component is the MagicBar, which is a widget that can be added
to any Qt application. It will then allow the user to configure and connect
to Arkitekt, and configure settings.
"""

try:
    import qtpy  # noqa: F401
except ImportError as e:
    raise ImportError(
        "arkitekt.qt requires a Qt binding via qtpy, which is not installed. "
        'Install it with: pip install "arkitekt[qt]"'
    ) from e

from .magic_bar import MagicBar
from .builders import qt
from .types import *

__all__ = ["MagicBar", "qt", "QtApp"]
