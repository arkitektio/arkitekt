FROM python:{__python_version__}-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

RUN mkdir /app
WORKDIR /app

# Outside /app, so copying the project below cannot replace it with a host .venv.
ENV UV_PROJECT_ENVIRONMENT=/opt/venv
COPY pyproject.toml uv.lock /app/
RUN uv sync --frozen --no-dev

ENV PATH="/opt/venv/bin:$PATH"

# The whole project: the app target may be any module in it, not only app.py.
COPY . /app

# The version of this build, when it is not the one the source declares: a build from
# a branch is passed it by `arkitekt plugin release`. Empty for a release proper.
ARG ARKITEKT_APP_VERSION=""
ENV ARKITEKT_APP_VERSION=$ARKITEKT_APP_VERSION
