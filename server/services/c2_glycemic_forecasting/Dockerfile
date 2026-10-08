# Build from the repository root: docker build -f server/services/c2_glycemic_forecasting/Dockerfile .
FROM python:3.11-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY server ./server
RUN uv sync --frozen --no-dev --package c2-glycemic-forecasting

EXPOSE 8002
CMD ["uvicorn", "c2_glycemic_forecasting.main:app", "--host", "0.0.0.0", "--port", "8002"]
