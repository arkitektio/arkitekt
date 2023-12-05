""" Utility functions for the Qt UI. """

import os

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(THIS_DIR, "assets")


def get_image_path(
    image_name: str, dark_mode: bool = False, assets_dir: str = ASSETS_DIR
) -> str:
    """Get the path to an image.

    Parameters
    ----------
    image_name : str
        Name of the image.
    dark_mode : bool, optional
        Whether to use the dark mode image, by default False.
    assets_dir : str, optional
        Directory where the assets are stored, by default ASSETS_DIR.

    Returns
    -------
    str
        Path to the image.
    """
    if dark_mode:
        return os.path.join(assets_dir, f"dark/{image_name}")
    return os.path.join(assets_dir, f"light/{image_name}")
