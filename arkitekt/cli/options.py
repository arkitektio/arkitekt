"""Shared Typer option definitions.

Connection options: `run dev|prod`, `call remote` and `login` take the same fakts
options (`--force` is the agent's, so only a run has it). They describe how a run connects, so they go to the runner
(:func:`arkitekt.connect` / :func:`arkitekt.arun`), never onto the App: the App is
the user's declaration and the command line does not rewrite it.

Defining each once as an `Annotated` alias keeps flags, help, envvars and types
identical across commands; each command still supplies its own default at the call
site (e.g. `url: UrlOption = DEFAULT_ARKITEKT_URL`).
"""

from enum import Enum
from pathlib import Path
from typing import Annotated, Optional

import typer


#: The panels `--help` groups the connection options into: where, as whom, with
#: which saved session, and how the agent registers.
SERVER_PANEL = "Server"
LOGIN_PANEL = "Login"
SESSION_PANEL = "Session"
AGENT_PANEL = "Agent"


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
        help="The Arkitekt server to connect to",
        envvar="FAKTS_URL",
        rich_help_panel=SERVER_PANEL,
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
        rich_help_panel=LOGIN_PANEL,
    ),
]

#: A redeem token used to authenticate. Callers default this to ``None``.
RedeemTokenOption = Annotated[
    Optional[str],
    typer.Option(
        "--redeem-token",
        "-r",
        help="A redeem token: provisions this app and logs it in without a browser",
        envvar="FAKTS_REDEEM_TOKEN",
        rich_help_panel=LOGIN_PANEL,
    ),
]

#: Force registration, taking over an existing connection. Callers default to ``False``.
ForceOption = Annotated[
    bool,
    typer.Option(
        "--force",
        "-f",
        help="Take over when another instance of this app is already connected (it is disconnected)",
        envvar="ARKITEKT_FORCE",
        rich_help_panel=AGENT_PANEL,
    ),
]

#: Run without an interactive UI. Callers default this to ``False``.
HeadlessOption = Annotated[
    bool,
    typer.Option(
        "--headless",
        help="Print the login link instead of opening a browser (the login itself is the same)",
        envvar="ARKITEKT_HEADLESS",
        rich_help_panel=LOGIN_PANEL,
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

#: Neither read nor write the fakts cache. Callers default this to ``False``.
SkipCacheOption = Annotated[
    bool,
    typer.Option(
        "--skip-cache",
        help="Ignore the saved session and save none: log in, for this run only",
        envvar="ARKITEKT_SKIP_CACHE",
        rich_help_panel=SESSION_PANEL,
    ),
]

#: Log in again even when a session is cached, and cache the new one.
ReauthOption = Annotated[
    bool,
    typer.Option(
        "--reauth",
        help=(
            "Log in again and replace the saved session: for a wrong user or "
            "organization. `arkitekt logout` forgets it instead."
        ),
        envvar="ARKITEKT_REAUTH",
        rich_help_panel=SESSION_PANEL,
    ),
]

#: The app context, as ``module:attr``: an instance of the class the App declared
#: (``App(..., app_context=Config)``), or a zero-argument factory of one.
ContextOption = Annotated[
    Optional[str],
    typer.Option(
        "--context",
        help=(
            "The app context, as module:attr -- an instance of the class the App "
            "declared with app_context=, or a zero-argument callable returning one."
        ),
    ),
]

#: A YAML or JSON file holding the app context, validated by the declared class.
ContextFileOption = Annotated[
    Optional[Path],
    typer.Option(
        "--context-file",
        help=(
            "A YAML or JSON file holding the app context; validated by the class "
            "the App declared with app_context=, which must be a pydantic model."
        ),
        exists=True,
        dir_okay=False,
        readable=True,
    ),
]
