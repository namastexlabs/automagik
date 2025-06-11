#!/bin/bash
# entrypoint.sh - Initialize Claude Code container environment

set -e

# Load workflow configuration
WORKFLOW_DIR="${WORKFLOW_DIR:-/workspace/workflow}"
if [ -f "$WORKFLOW_DIR/.env" ]; then
    source "$WORKFLOW_DIR/.env"
fi

# Set defaults
GIT_BRANCH="${GIT_BRANCH:-NMSTX-187-langgraph-orchestrator-migration}"
WORKSPACE_DIR="${WORKSPACE_DIR:-/workspace/am-agents-labs}"

echo "🏗️ Initializing Claude Code container..."
echo "   Workflow: $WORKFLOW_DIR"
echo "   Branch: $GIT_BRANCH"
echo "   Workspace: $WORKSPACE_DIR"

# Set repository URL (use environment variable or default)
REPO_URL="${REPOSITORY_URL:-https://github.com/namastexlabs/am-agents-labs.git}"

# Extract repository name from URL
REPO_NAME=$(basename "$REPO_URL" .git)

# Update workspace directory to use dynamic repo name
WORKSPACE_DIR="/workspace/$REPO_NAME"

# Clone repository if not exists
if [ ! -d "$WORKSPACE_DIR" ]; then
    echo "📦 Cloning repository from $REPO_URL..."
    cd /workspace
    
    if [ -n "$GITHUB_TOKEN" ]; then
        # Parse URL and insert token
        REPO_URL_WITH_TOKEN=$(echo "$REPO_URL" | sed "s|https://|https://oauth2:${GITHUB_TOKEN}@|")
        git clone -b "$GIT_BRANCH" "$REPO_URL_WITH_TOKEN" "$REPO_NAME"
    else
        git clone -b "$GIT_BRANCH" "$REPO_URL" "$REPO_NAME"
    fi
    
    cd "$WORKSPACE_DIR"
    git config user.name "Claude Code Agent"
    git config user.email "claude@automagik-agents.ai"
    
    echo "✅ Repository cloned and configured"
else
    echo "📁 Using existing repository at $WORKSPACE_DIR"
    cd "$WORKSPACE_DIR"
fi

# Set up environment from workflow
if [ -f "$WORKFLOW_DIR/.env" ]; then
    echo "🔧 Copying workflow environment..."
    cp "$WORKFLOW_DIR/.env" .env
fi

# Set up Claude credentials
if [ -f "$WORKFLOW_DIR/.credentials.json" ]; then
    echo "🔑 Setting up Claude credentials..."
    mkdir -p /home/claude/.claude
    ln -sf "$WORKFLOW_DIR/.credentials.json" /home/claude/.claude/.credentials.json
fi

# Start automagik-agents services if docker-compose exists
if [ -f "docker/docker-compose.yml" ]; then
    echo "🚀 Starting automagik-agents services..."
    docker-compose -f docker/docker-compose.yml up -d
    
    # Wait for services to be ready
    echo "⏳ Waiting for services to initialize..."
    sleep 20
    
    echo "✅ Services started"
fi

# Build Claude command with workflow configuration
CLAUDE_CMD="claude --dangerously-skip-permissions --output-format json"

# Add MCP configuration if available
if [ -f "$WORKFLOW_DIR/.mcp.json" ]; then
    CLAUDE_CMD="$CLAUDE_CMD --mcp-config $WORKFLOW_DIR/.mcp.json"
fi

# Add allowed tools if available
if [ -f "$WORKFLOW_DIR/allowed_tools.json" ]; then
    ALLOWED_TOOLS=$(cat "$WORKFLOW_DIR/allowed_tools.json" | jq -r 'join(",")')
    CLAUDE_CMD="$CLAUDE_CMD --allowedTools $ALLOWED_TOOLS"
fi

# Add system prompt if available
if [ -f "$WORKFLOW_DIR/prompt.md" ]; then
    CLAUDE_CMD="$CLAUDE_CMD --append-system-prompt \"$(cat $WORKFLOW_DIR/prompt.md)\""
fi

# Execute Claude with the provided arguments
echo "🤖 Starting Claude CLI..."
echo "Command: $CLAUDE_CMD $@"

cd "$WORKSPACE_DIR"
eval "$CLAUDE_CMD \"$@\"" > /tmp/claude-output.json

# Parse Claude output
CLAUDE_EXIT_CODE=$?
CLAUDE_SESSION_ID=$(jq -r '.session_id // "unknown"' /tmp/claude-output.json 2>/dev/null || echo "unknown")
CLAUDE_RESULT=$(jq -r '.result // .content // "No result"' /tmp/claude-output.json 2>/dev/null || echo "No result")

echo "🔍 Claude execution completed with exit code: $CLAUDE_EXIT_CODE"

# Generate commit message using Claude if changes exist
if [ -n "$(git status --porcelain)" ]; then
    echo "📝 Generating commit for changes..."
    
    git add -A
    
    # Use Claude to generate and apply commit
    claude \
        --dangerously-skip-permissions \
        --max-turns 1 \
        --output-format json \
        --append-system-prompt "You are a git commit message generator. Analyze the staged changes using 'git diff --cached' and commit them with a semantic commit message following conventional commits format (type(scope): description). Use the Bash tool to run git diff, analyze the changes, then commit with an appropriate message." \
        "Generate a commit message for the staged changes and commit them" > /tmp/commit-result.json
    
    COMMIT_EXIT_CODE=$?
    COMMIT_RESULT=$(jq -r '.result // "Commit completed"' /tmp/commit-result.json 2>/dev/null || echo "Commit completed")
    
    echo "📤 Commit result: $COMMIT_RESULT"
    
    # Push changes if git remote exists and we have credentials
    if git remote get-url origin >/dev/null 2>&1 && [ -n "$GITHUB_TOKEN" ]; then
        echo "🚀 Pushing changes to remote..."
        git push origin "$GIT_BRANCH" || echo "⚠️ Push failed, changes are committed locally"
    fi
else
    echo "📭 No changes to commit"
fi

# Cleanup services
if [ -f "docker/docker-compose.yml" ]; then
    echo "🧹 Stopping services..."
    docker-compose -f docker/docker-compose.yml down
fi

# Output final result in JSON format for container management
echo "{\"session_id\": \"$CLAUDE_SESSION_ID\", \"result\": \"$CLAUDE_RESULT\", \"exit_code\": $CLAUDE_EXIT_CODE}"

exit $CLAUDE_EXIT_CODE