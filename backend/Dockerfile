FROM python:3.13-slim

# uv for fast, reproducible installs.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Install deps first for better layer caching.
COPY pyproject.toml ./
RUN uv sync

COPY app ./app

# Railway injects PORT; default to 8000 for local docker runs.
ENV PORT=8000
EXPOSE 8000

CMD uv run uvicorn app.main:app --host 0.0.0.0 --port ${PORT}
