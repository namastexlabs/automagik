FROM python:3.11-slim

# Add build arg for port
ARG AUTOMAGIK_API_PORT=18881

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

# System dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gcc \
        libc6-dev \
        libpq-dev \
        libffi-dev \
        postgresql-client \
        curl \
        bash \
        build-essential \
        git \
        ca-certificates \
        gnupg \
    && mkdir -p /etc/apt/keyrings \
    && curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg \
    && echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_20.x nodistro main" | tee /etc/apt/sources.list.d/nodesource.list \
    && apt-get update \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir uv

WORKDIR /app

# Install dependencies only (without building project)
COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --no-install-project

# Copy source code and install project
COPY src/ ./src/
RUN uv pip install --no-deps -e .

ENV AUTOMAGIK_ENV=production
EXPOSE ${AUTOMAGIK_API_PORT}

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:${AUTOMAGIK_API_PORT}/health || exit 1

CMD ["uv", "run", "python", "-m", "src"]
