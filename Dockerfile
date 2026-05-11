# ─────────────────────────────────────────────────────────────────────────────
# Stage 1: Builder — install Python dependencies
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

# Build deps (needed for some packages with C extensions)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir --prefix=/install -r requirements.txt


# ─────────────────────────────────────────────────────────────────────────────
# Stage 2: Runtime — slim final image
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

# Security: non-root user
RUN groupadd -r botuser && useradd -r -g botuser -d /app botuser

WORKDIR /app

# No extra system packages needed for SQLite (built into Python)
# If you switch to PostgreSQL, uncomment:
# RUN apt-get update && apt-get install -y --no-install-recommends libpq5 && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from builder
COPY --from=builder /install /usr/local

# Copy application source (excluding files in .dockerignore)
COPY --chown=botuser:botuser . .

# Create persistent data directories
RUN mkdir -p logs data && chown -R botuser:botuser logs data

# Switch to non-root user
USER botuser

# Ensure Python output is not buffered (important for loguru)
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Health check
HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import bot.config" || exit 1

CMD ["python", "-m", "bot.main"]
