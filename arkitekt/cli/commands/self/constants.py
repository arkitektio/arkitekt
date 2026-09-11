"""Canonical list of Arkitekt ecosystem packages.

These are the separately versioned PyPI distributions that make up the Arkitekt
SDK. The ``self upgrade`` command checks each installed one against PyPI and
upgrades the outdated ones. Non-arkitekt libraries (click, semver, rich-click,
watchfiles, platformdirs, py-machineid, ...) are intentionally excluded.

Names are the PyPI/distribution names (hyphenated).
"""

from typing import List

ARKITEKT_PACKAGES: List[str] = [
    "arkitekt",
    "rekuest",
    "mikro",
    "fakts",
    "rath",
    "koil",
    "kabinet",
    "elektro",
    "fluss",
    "unlok-next",
    "kraph",
    "alpaka",
    "turms",
    "reaktion-next",
    "lovekit",
]
