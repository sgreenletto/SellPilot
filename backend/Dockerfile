FROM ghcr.io/astral-sh/uv:0.11.27 AS uv

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/backend/.venv/bin:$PATH"

WORKDIR /app/backend

COPY --from=uv /uv /uvx /bin/
COPY backend/pyproject.toml backend/uv.lock backend/README.md ./
COPY backend/src ./src
RUN uv sync --frozen --no-dev

COPY backend/alembic.ini ./alembic.ini
COPY backend/migrations ./migrations
COPY data /app/data

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --start-period=20s --retries=5 \
  CMD python -c "from urllib.request import urlopen; urlopen('http://127.0.0.1:8000/api/v1/health/live', timeout=2)"

CMD ["uv", "run", "--no-sync", "sellpilot-start-api"]
