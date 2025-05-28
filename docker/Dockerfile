# Automagik Agents Dockerfile - Optimized
FROM python:3.11-alpine

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install system dependencies efficiently
RUN apk add --no-cache --virtual .build-deps \
    gcc \
    musl-dev \
    postgresql-dev \
    libffi-dev \
    && apk add --no-cache \
    postgresql-client \
    curl \
    bash \
    && pip install --no-cache-dir uv

# Set working directory
WORKDIR /app

# Copy dependency files first (for better layer caching)
# Ensure uv.lock (TOML format) is copied
COPY pyproject.toml uv.lock ./

# Copy source code
COPY src/ ./src/

# Install dependencies from the TOML uv.lock using uv sync
# --frozen ensures it uses the lockfile without trying to update it
RUN uv sync --frozen

# Clean up build dependencies to reduce image size
RUN apk del .build-deps

# Set environment variables
ENV AM_ENV=production

# Expose port for API
EXPOSE 18881

# Health check (use the venv's python)
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:18881/health || exit 1

# Command to run the application (use the venv's python)
CMD [".venv/bin/python", "-m", "src"]
