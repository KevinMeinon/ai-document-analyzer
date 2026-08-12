FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim AS builder

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src ./src
RUN uv sync --frozen --no-dev


FROM python:3.14-slim-bookworm AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        libgl1 \
        libglib2.0-0 \
        libgomp1 \
        libreoffice-writer \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /app /app

RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /data/chroma /data/logs /data/uploads \
    && chown -R appuser:appuser /app /data

USER appuser

EXPOSE 8000
CMD ["uvicorn", "document_analyzer.main:app", "--host", "0.0.0.0", "--port", "8000"]


FROM runtime AS development

CMD ["uvicorn", "document_analyzer.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
