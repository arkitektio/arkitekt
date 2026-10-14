FROM python:{__python_version__}-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

RUN mkdir /app
WORKDIR /app

# Outside /app, so copying the project below cannot replace it with a host .venv.
ENV UV_PROJECT_ENVIRONMENT=/opt/venv
# The dependencies alone first, so a change to the code does not install them again.
COPY pyproject.toml uv.lock /app/
RUN uv sync --frozen --no-dev --no-install-project

ENV PATH="/opt/venv/bin:$PATH"

# The whole project: the app target may be any module in it, not only app.py.
COPY . /app
# And the project itself, when it is a package (one with a build backend).
RUN uv sync --frozen --no-dev

# The version of this build, when it is not the one the source declares: a build from
# a branch is passed it by `arkitekt plugin release`. Empty for a release proper.
ARG ARKITEKT_APP_VERSION=""
ENV ARKITEKT_APP_VERSION=$ARKITEKT_APP_VERSION
