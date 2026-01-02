# syntax=docker/dockerfile:1.7-labs

# Builder image: uv + Python already available
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

# Improve runtime performance and container compatibility
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0

WORKDIR /app

# Install dependencies first for better layer caching
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev

# Copy application code and install the project into the venv
COPY . /app

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev


# Runtime image: small, no uv included
FROM python:3.12-slim-bookworm AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH="/app/src" \
    PATH="/app/.venv/bin:$PATH"

# Run as a non-root user
RUN groupadd --system --gid 999 nonroot \
 && useradd --system --uid 999 --gid 999 --create-home nonroot

WORKDIR /app

# Copy the fully-built app + venv from the builder
COPY --from=builder --chown=nonroot:nonroot /app /app

USER nonroot

EXPOSE 4040

# Default to running the API; docker-compose overrides this for workers
CMD ["uvicorn", "src.evaluator.main:app", "--host", "0.0.0.0", "--port", "4040"]
