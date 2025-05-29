#!/bin/bash
# setup_worktrees.sh - Initialize worktrees for all agents

set -euo pipefail

BASE_REPO="/root/workspace/am-agents-labs"
EPIC_ID="${1:-}"

if [[ -z "$EPIC_ID" ]]; then
    echo "Usage: $0 <epic_id>"
    echo "Example: $0 127"
    exit 1
fi

echo "Setting up worktrees for epic NMSTX-${EPIC_ID}..."

cd "$BASE_REPO"

# Setup worktrees
worktrees=(
    "core:$BASE_REPO/../am-agents-core"
    "api:$BASE_REPO/../am-agents-api"
    "tools:$BASE_REPO/../am-agents-tools"
    "tests:$BASE_REPO/../am-agents-tests"
)

for worktree in "${worktrees[@]}"; do
    IFS=':' read -r component path <<< "$worktree"
    branch="NMSTX-${EPIC_ID}-${component}"
    
    if [[ -d "$path" ]]; then
        echo "⚠️  Worktree exists: $path"
        echo "   Removing old worktree..."
        git worktree remove "$path" --force 2>/dev/null || true
    fi
    
    echo "✓ Creating worktree: $branch at $path"
    git worktree add "$path" -b "$branch"
done

echo ""
echo "✅ Worktrees created successfully!"
echo ""
echo "Agent workspace mapping:"
echo "  Alpha → $BASE_REPO (main)"
echo "  Beta  → $BASE_REPO/../am-agents-core"
echo "  Delta → $BASE_REPO/../am-agents-api"
echo "  Epsilon → $BASE_REPO/../am-agents-tools"
echo "  Gamma → $BASE_REPO/../am-agents-tests"