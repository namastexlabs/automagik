# Stage 1: Builder
FROM python:3.11-alpine AS builder

# Set environment variables for builder stage
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install build-time system dependencies for z3-solver and other packages
# alpine-sdk includes make, gcc, etc.
# cmake is required by z3-solver
# postgresql-dev and libffi-dev for psycopg2 and cffi if they have native parts
RUN apk add --no-cache \
    alpine-sdk \
    cmake \
    postgresql-dev \
    libffi-dev
    # curl is not strictly needed here anymore if we use COPY --from for uv

# Install uv in the builder stage - MÉTODO OFICIAL
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency files AND source code before sync
COPY pyproject.toml uv.lock ./          
COPY src/ ./src/  

# Install Python dependencies, including compiling z3-solver and the local project
RUN uv sync --frozen

# Stage 2: Runtime
FROM python:3.11-alpine AS runtime

# Set environment variables for runtime stage
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV AM_ENV=production
# Ensure Python from our venv is found first
ENV PATH="/app/.venv/bin:$PATH"

# Install runtime system dependencies
# postgresql-client for running db commands if needed by app, curl for healthcheck
RUN apk add --no-cache \
    postgresql-client \
    curl \
    bash # If any scripts use bash

WORKDIR /app

# Copy the virtual environment with compiled dependencies from the builder stage
COPY --from=builder /app/.venv ./.venv/

# Copy the application source code (já que o venv pode ter referências a ele se instalado em modo editável)
# Embora o venv seja autocontido para dependências, copiar src/ garante consistência.
COPY --from=builder /app/src ./src/

# Expose port for API
EXPOSE 18881

# Health check (uses Python from the copied venv due to PATH modification)
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:18881/health || exit 1

# Command to run the application (uses Python from the copied venv)
CMD ["python", "-m", "src"]
