import semver
from .errors import ValidationError, cli_error


def is_valid_semver(param: str, loaded=False) -> semver.VersionInfo:
    """Checks if the param is a valid semver version and returns it as a semver object"""
    if not semver.Version.is_valid(param):
        if loaded:
            cli_error(
                "Manifest version incorrect, please update your manifest to a valid semver version  [link=https://semver.org]semver[/link]."
            )

        raise ValidationError(
            "ArkitektNext versions need to follow semantic versioning. Please choose a correct format (examples: 0.0.0, 0.1.0, 0.0.0-alpha.1)"
        )
    return semver.Version.parse(param)
