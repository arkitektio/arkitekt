"""Shared Typer option definitions.

Two families live here:

- **Connection options** -- `app run dev|prod|tests` and `app call remote` all take
  the same fakts/builder options.
- **Deployment options** -- every `server <kind> init` takes the same
  template/wizard/port/backend options.

Defining each once as an `Annotated` alias keeps flags, help, envvars and types
identical across commands; each command still supplies its own default at the call
site (e.g. `url: UrlOption = DEFAULT_ARKITEKT_URL`).
"""

from enum import Enum
from typing import Annotated, List, Optional

import typer


class LogLevel(str, Enum):
    """The logging levels accepted by the run commands."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


#: The fakts_next endpoint URL. Callers default this to ``DEFAULT_ARKITEKT_URL``.
UrlOption = Annotated[
    str,
    typer.Option(
        "--url",
        "-u",
        help="The fakts_next url for connection",
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
        help="The redeem token used to authenticate against the fakts_next instance",
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


# --- Deployment options (hub / coord / hubinator / engine) -------------------
# Every deployment group's `init` used to redeclare these with copy-pasted help.

#: Config template to start from. ``None`` (the default everywhere) runs the wizard.
TemplateOption = Annotated[
    Optional[str],
    typer.Option(
        "--template",
        "-t",
        help="Config template (stable, dev, default, minimal). If omitted, the interactive wizard runs instead.",
    ),
]

#: Force the interactive wizard even when a template was given.
WizardOption = Annotated[
    bool,
    typer.Option("--wizard", "-w", help="Force the interactive configuration wizard."),
]

#: Accept every default and ask nothing.
UseDefaultOption = Annotated[
    bool,
    typer.Option("--default", "-d", help="Accept all defaults (skip the wizard, no prompts)."),
]

#: Repeatable service selection. Only meaningful for kinds carrying data services.
ServicesOption = Annotated[
    List[str],
    typer.Option(
        "--service",
        "-s",
        help="Enable exactly these services (repeatable). Defaults to the template's selection.",
    ),
]

#: Exposed HTTP port of the gateway.
PortOption = Annotated[
    Optional[int],
    typer.Option("--port", help="Exposed HTTP port."),
]

#: Exposed HTTPS port of the gateway.
SslPortOption = Annotated[
    Optional[int],
    typer.Option("--ssl-port", help="Exposed HTTPS port."),
]

#: Which container backend the generated deployment targets.
BackendOption = Annotated[
    str,
    typer.Option("--backend", help="Deployment backend (docker, podman, kubernetes)."),
]

#: Rekuest (provenance) server host. ``local`` runs rekuest as a core dependency.
RekuestServerOption = Annotated[
    Optional[str],
    typer.Option(
        "--rekuest-server",
        help="Rekuest (provenance) server host ('local' runs rekuest as a core dependency).",
    ),
]

#: Optional positional deployment directory; falls back to the global ``--work-dir``.
PathArgument = Annotated[
    Optional[str],
    typer.Argument(help="Deployment directory. Defaults to the global --work-dir."),
]
