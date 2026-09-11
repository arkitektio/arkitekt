FROM python:{__python_version__}-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

RUN mkdir /app
WORKDIR /app

COPY pyproject.toml uv.lock /app/
RUN uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:$PATH"

COPY .arkitekt_next /app/.arkitekt_next
COPY app.py /app/app.py
