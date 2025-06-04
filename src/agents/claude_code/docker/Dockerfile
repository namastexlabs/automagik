# Claude-Code Agent Container
# Based on project's existing Alpine setup with Claude CLI integration

FROM python:3.11-alpine

# System dependencies (matching project's docker/Dockerfile)
RUN apk add --no-cache --virtual .build-deps gcc musl-dev postgresql-dev libffi-dev \
    && apk add --no-cache postgresql-client curl bash libc6-compat git openssh-client \
    nodejs npm jq docker docker-compose \
    && pip install --no-cache-dir uv

# Install Claude CLI globally
RUN npm install -g @anthropic-ai/claude-code

# Create workspace and claude user
RUN adduser -D claude
WORKDIR /workspace

# Copy scripts
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Create mount points for volumes
RUN mkdir -p /workspace/workflow /workspace/am-agents-labs /home/claude/.claude /home/claude/.ssh \
    && chown -R claude:claude /workspace /home/claude

# Switch to non-root user
USER claude

# Set default environment variables
ENV GIT_BRANCH=NMSTX-187-langgraph-orchestrator-migration
ENV WORKSPACE_DIR=/workspace/am-agents-labs
ENV WORKFLOW_DIR=/workspace/workflow

ENTRYPOINT ["/entrypoint.sh"]