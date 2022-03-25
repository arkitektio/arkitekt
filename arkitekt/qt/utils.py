import os

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(THIS_DIR, "assets")


def get_image_path(image_name, dark_mode=False, assets_dir=ASSETS_DIR):
    if dark_mode:
        return os.path.join(assets_dir, f"dark/{image_name}")
    return os.path.join(assets_dir, f"light/{image_name}")
