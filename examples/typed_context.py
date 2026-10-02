# /// script
# requires-python = ">=3.11"
# dependencies = ["arkitekt[rekuest]>=5", "tifffile>=2024.5.22", "numpy>=1.26"]
# ///
"""Offering: configuration that belongs to the run, not to the caller.

Run:  uv run --script examples/typed_context.py /path/to/images 0.325

The scope a microscope app runs in — which directory this machine writes to,
what its pixel size is — is not something a caller should pass per call. Declare
it as the app context and hand it to `run` once:

    app = App("acquire", app_context=Setup)   # -> App[Setup]
    run(app, context=Setup(...))              # context= is now required

Every action (and startup hook) annotated with `Setup` is handed that instance.
Leave `context=` out and the run refuses before it connects — and a type checker
flags it, because `App[Setup]` narrows `run`.
"""

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

import numpy as np
import tifffile

from arkitekt import App, Description, run


@dataclass
class Setup:
    """What this particular installation is."""

    image_dir: Path
    pixel_size_um: float


app = App("typed-context", "0.1.0", app_context=Setup)


@app.action
def list_images(setup: Setup) -> list[str]:
    """List Images

    The TIFFs in this installation's image directory.
    """
    return sorted(p.name for p in setup.image_dir.glob("*.tif"))


@app.action
def physical_size(
    setup: Setup,
    name: Annotated[str, Description("A file name from `list_images`")],
) -> float:
    """Physical Size

    The width of an image in micrometers, using this installation's pixel size.
    """
    array = np.asarray(tifffile.imread(setup.image_dir / name))
    return float(array.shape[-1] * setup.pixel_size_um)


if __name__ == "__main__":
    image_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    pixel_size = float(sys.argv[2]) if len(sys.argv) > 2 else 0.1
    run(app, context=Setup(image_dir=image_dir, pixel_size_um=pixel_size))
