# Stage 1: Build — install dependencies into wheel cache
FROM python:3.12-slim AS builder

WORKDIR /app

# System deps needed to compile wheels (libpq for asyncpg/psycopg2)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# Pre-build all wheels (including gunicorn) into a local dir
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt gunicorn

# ─────────────────────────────────────────────────────────────────────────────
# Stage 2: Final runtime image — lean, no build tools
FROM python:3.12-slim

WORKDIR /app

# Only runtime C libraries needed (libpq)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Install pre-built wheels from stage 1
COPY --from=builder /app/wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels

# Copy application source
COPY . .

# Non-root user for security
RUN useradd -m -r appuser && chown -R appuser /app
USER appuser

EXPOSE 8000

# Gunicorn + UvicornWorker for production; tune --workers based on CPU cores
CMD ["gunicorn", "main:app", \
     "--workers", "4", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8000", \
     "--timeout", "60", \
     "--graceful-timeout", "30", \
     "--access-logfile", "-"]
