from enum import Enum
import os
import rich_click as click
from .types import Requirement


class Framework(str, Enum):
    VANILLA = "vanilla"
    TENSORFLOW = "tensorflow"
    PYTORCH = "pytorch"


def check_dl_frameworks():
    import site
    import sys

    site_packages = site.getsitepackages()
    site_packages.append(sys.prefix)

    frameworks = {
        "tensorflow": Framework.TENSORFLOW,
        "torch": Framework.PYTORCH,
        "torchvision": Framework.PYTORCH,
        "tensorflow-gpu": Framework.TENSORFLOW,
        "torch-gpu": Framework.PYTORCH,
        "torchvision-gpu": Framework.PYTORCH,
    }

    included_frameworks = set()

    for key, value in frameworks.items():
        for site_package in site_packages:
            if os.path.exists(os.path.join(site_package, key)):
                included_frameworks.add(value)
    return included_frameworks


def inspect_requirements(automatic=False):
    requirements = []
    reasons = []
    frameworks = check_dl_frameworks()
    if frameworks:
        yes = (
            True
            if automatic
            else click.ask(
                "It seems like you are using a deep learning framework. Would you like to require GPU support?",
            )
        )
        if yes:
            requirements.append(Requirement.GPU)
            reasons.append(
                "Deep learning framework detected ('{}')".format(", ".join(frameworks))
            )

    return requirements, reasons
