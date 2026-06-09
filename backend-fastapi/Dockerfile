FROM python:3.12-slim-bookworm

# Install uv (fast, lockfile-accurate installs) — keeps the image in sync with
# pyproject.toml / uv.lock instead of a hand-maintained pip list.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Install dependencies first (better layer caching). Only project metadata +
# lockfile are needed to resolve the environment.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# App code
COPY app ./app

ENV PORT=8080
# Put the uv-managed venv on PATH so `python`/`uvicorn` resolve to it.
ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8080

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
