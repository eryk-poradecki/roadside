# Backend image (ADR 0007): uv builder -> slim runtime, non-root, one uvicorn worker.
# The `claude` CLI is deliberately absent, so the CLI provider can't ship (ADR 0004).

FROM python:3.14-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:0.13.7 /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /app
# Runtime dependencies only. The app runs from source (migrations sit next to it), not as a wheel.
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

FROM python:3.14-slim
RUN groupadd --system --gid 10001 roadside \
 && useradd --system --uid 10001 --gid roadside --no-create-home roadside \
 && mkdir /data \
 && chown roadside:roadside /data
WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY app ./app
COPY migrations ./migrations
COPY recordings ./recordings
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    # Repeated in compose.yaml's `environment:`, which must beat an optional backend/.env.
    DATABASE_PATH=/data/roadside.db \
    UPLOAD_DIR=/data/uploads \
    LLM_RECORDINGS_DIR=/app/recordings
# The database and uploads live here; compose mounts a named volume over it.
VOLUME /data
USER roadside
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"]
# One worker: AI turns are serialised by an in-process lock (ADR 0005). The proxy in front
# (nginx) is on a private network, so its forwarded headers are trusted.
CMD ["uvicorn", "--factory", "app.main:create_app", "--host", "0.0.0.0", "--port", "8000", \
     "--workers", "1", "--proxy-headers", "--forwarded-allow-ips", "*"]
