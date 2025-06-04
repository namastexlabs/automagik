FROM python:3.11-alpine

# Add build arg for port
ARG AM_PORT=18881

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

# System dependencies
RUN apk add --no-cache --virtual .build-deps gcc musl-dev postgresql-dev libffi-dev \
    && apk add --no-cache postgresql-client curl bash libc6-compat \
    && pip install --no-cache-dir uv

WORKDIR /app

# Install dependencies only (without building project)
COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --no-install-project

# Copy source code and install project
COPY src/ ./src/
RUN uv pip install --no-deps -e .

# Cleanup
RUN apk del .build-deps

ENV AM_ENV=production
EXPOSE ${AM_PORT}

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:${AM_PORT}/health || exit 1

CMD ["uv", "run", "python", "-m", "src"]
