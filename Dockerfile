# AI Flywheel Backend — Python FastAPI + Temporal Worker
FROM python:3.12-slim AS base

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY pyproject.toml ./
RUN pip install --no-cache-dir -e .

# Copy application
COPY ai_flywheel/ ./ai_flywheel/
COPY alembic/ ./alembic/
COPY alembic.ini ./
COPY run_api.py ./

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default: run API server
CMD ["uvicorn", "ai_flywheel.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
