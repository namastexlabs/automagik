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
COPY pyproject.toml ./

# Install dependencies only (without the project itself)
RUN uv pip install --system --no-cache-dir \
    python-dotenv>=1.0.1 \
    notion-client>=2.3.0 \
    rich>=13.9.4 \
    logfire>=3.6.1 \
    fastapi>=0.104.1 \
    uvicorn>=0.24.0 \
    pydantic-settings>=2.8.0 \
    typer>=0.9.0 \
    discord-py>=2.4.0 \
    psycopg2-binary>=2.9.10 \
    pydantic-ai>=0.0.36 \
    pytest>=8.3.5 \
    requests>=2.32.3 \
    pydantic-ai-slim[duckduckgo]>=0.0.42 \
    pydantic[email]>=2.10.6 \
    google-api-python-client>=2.165.0 \
    google-auth-httplib2>=0.2.0 \
    google-auth-oauthlib>=1.2.1 \
    pytz>=2025.2 \
    supabase>=2.15.0 \
    httpx>=0.27.0

# Copy source code (this layer changes frequently)
COPY src/ ./src/

# Install the project in editable mode without dependencies
RUN uv pip install --system --no-cache-dir -e . --no-deps

# Clean up build dependencies to reduce image size
RUN apk del .build-deps

# Set environment variables
ENV AM_ENV=production

# Expose port for API
EXPOSE 8881

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:8881/health || exit 1

# Command to run the application
CMD ["python", "-m", "src"]
