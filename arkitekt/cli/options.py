"""Shared Typer option definitions.

Connection options: `run dev|prod` and `call remote` all take the same
fakts/builder options.

Defining each once as an `Annotated` alias keeps flags, help, envvars and types
identical across commands; each command still supplies its own default at the call
site (e.g. `url: UrlOption = DEFAULT_ARKITEKT_URL`).
"""

from enum import Enum
from typing import Annotated, Optional

import typer


class LogLevel(str, Enum):
    """The logging levels accepted by the run commands."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


#: The fakts endpoint URL. Callers default this to ``DEFAULT_ARKITEKT_URL``.
UrlOption = Annotated[
    str,
    typer.Option(
        "--url",
        "-u",
        help="The fakts url for connection",
        envvar="FAKTS_URL",
    ),
]

#: The dotted path to the builder function. Callers default to the easy builder.
BuilderOption = Annotated[
    str,
    typer.Option(
        "--builder",
        "-b",
        help="The builder for this run",
        envvar="ARKITEKT_BUILDER",
    ),
]

#: A pre-issued fakts credential, as ``client_id:refresh_token``.
#: Callers default this to ``None``.
TokenOption = Annotated[
    Optional[str],
    typer.Option(
        "--token",
        "-t",
        help=(
            "A previously issued credential, as 'client_id:refresh_token'. "
            "Both halves are required: the token endpoint authenticates the "
            "client before it validates the refresh token. To provision a new "
            "app instead, use --redeem-token."
        ),
        envvar="FAKTS_TOKEN",
    ),
]

#: A redeem token used to authenticate. Callers default this to ``None``.
RedeemTokenOption = Annotated[
    Optional[str],
    typer.Option(
        "--redeem-token",
        "-r",
        help="The redeem token used to authenticate against the fakts instance",
        envvar="FAKTS_REDEEM_TOKEN",
    ),
]

#: Force registration, taking over an existing connection. Callers default to ``False``.
ForceOption = Annotated[
    bool,
    typer.Option(
        "--force",
        "-f",
        help="Force registration, kicking any existing connection for this agent and taking over",
        envvar="ARKITEKT_FORCE",
    ),
]

#: Run without an interactive UI. Callers default this to ``False``.
HeadlessOption = Annotated[
    bool,
    typer.Option(
        "--headless",
        help="Should we start headless",
        envvar="ARKITEKT_HEADLESS",
    ),
]

#: The logging level. Callers default this to ``LogLevel.ERROR``.
LogLevelOption = Annotated[
    LogLevel,
    typer.Option(
        "--log-level",
        "-l",
        help="The logging level to use",
        envvar="ARKITEKT_LOG_LEVEL",
    ),
]

#: Skip the fakts cache. Callers default this to ``False``.
NoCacheOption = Annotated[
    bool,
    typer.Option(
        "--no-cache",
        "-nc",
        help="Should we skip the cache",
        envvar="ARKITEKT_NO_CACHE",
    ),
]

#: Override the app version. Callers default this to ``None``.
VersionOption = Annotated[
    Optional[str],
    typer.Option(
        "--version",
        "-v",
        help="Override the version of the app",
        envvar="ARKITEKT_VERSION",
    ),
]
