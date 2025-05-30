#!/bin/bash
# setup_worktrees.sh - Initialize worktrees for all agents with proper branch handling

set -euo pipefail

BASE_REPO="/root/workspace/am-agents-labs"
EPIC_ID="${1:-}"
FORCE_RECREATE="${2:-false}"  # Optional second parameter to force recreate

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

if [[ -z "$EPIC_ID" ]]; then
    echo "Usage: $0 <epic_id> [force]"
    echo "Example: $0 127"
    echo "Example: $0 127 force  # Force recreate branches"
    exit 1
fi

echo -e "${BLUE}Setting up worktrees for epic NMSTX-${EPIC_ID}...${NC}"

cd "$BASE_REPO"

# Function to setup a single worktree
setup_worktree() {
    local component=$1
    local path=$2
    local branch="NMSTX-${EPIC_ID}-${component}"
    
    echo ""
    echo -e "${BLUE}Processing ${component}...${NC}"
    
    # Check if worktree exists
    if [[ -d "$path" ]]; then
        echo -e "${YELLOW}⚠️  Worktree exists at: $path${NC}"
        
        # Get current branch of worktree
        current_branch=$(cd "$path" && git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
        
        if [[ "$current_branch" == "$branch" ]] && [[ "$FORCE_RECREATE" != "force" ]]; then
            echo -e "${GREEN}✓ Worktree already on correct branch: $branch${NC}"
            echo "  Pulling latest changes..."
            (cd "$path" && git pull origin main --rebase 2>/dev/null || true)
            return 0
        else
            echo "  Current branch: $current_branch"
            echo "  Removing old worktree..."
            git worktree remove "$path" --force 2>/dev/null || true
        fi
    fi
    
    # Check if branch exists (locally or remotely)
    if git show-ref --verify --quiet "refs/heads/$branch"; then
        echo -e "${YELLOW}  Branch exists locally: $branch${NC}"
        
        if [[ "$FORCE_RECREATE" == "force" ]]; then
            echo "  Force mode: Deleting existing branch..."
            git branch -D "$branch" 2>/dev/null || true
            git worktree add "$path" -b "$branch"
        else
            echo "  Reusing existing branch..."
            git worktree add "$path" "$branch"
        fi
    elif git ls-remote --heads origin "$branch" | grep -q "$branch"; then
        echo -e "${YELLOW}  Branch exists remotely: $branch${NC}"
        
        if [[ "$FORCE_RECREATE" == "force" ]]; then
            echo "  Force mode: Creating fresh branch..."
            git worktree add "$path" -b "$branch"
        else
            echo "  Checking out remote branch..."
            git worktree add "$path" -b "$branch" "origin/$branch" 2>/dev/null || \
            git worktree add "$path" "$branch"
        fi
    else
        echo -e "${GREEN}  Creating new branch: $branch${NC}"
        git worktree add "$path" -b "$branch"
    fi
    
    # Ensure worktree is on latest main commits
    echo "  Syncing with main branch..."
    (cd "$path" && git pull origin main --rebase 2>/dev/null || true)
    
    echo -e "${GREEN}✓ Worktree ready: $component → $path${NC}"
}

# Setup worktrees
worktrees=(
    "core:$BASE_REPO/../am-agents-core"
    "api:$BASE_REPO/../am-agents-api"
    "tools:$BASE_REPO/../am-agents-tools"
    "tests:$BASE_REPO/../am-agents-tests"
)

# First, fetch latest from origin
echo -e "${BLUE}Fetching latest from origin...${NC}"
git fetch origin

for worktree in "${worktrees[@]}"; do
    IFS=':' read -r component path <<< "$worktree"
    setup_worktree "$component" "$path"
done

echo ""
echo -e "${GREEN}✅ Worktrees setup complete!${NC}"
echo ""
echo "Agent workspace mapping:"
echo "  Alpha → $BASE_REPO (main)"
echo "  Beta  → $BASE_REPO/../am-agents-core"
echo "  Delta → $BASE_REPO/../am-agents-api"
echo "  Epsilon → $BASE_REPO/../am-agents-tools"
echo "  Gamma → $BASE_REPO/../am-agents-tests"
echo ""
echo -e "${YELLOW}Tips:${NC}"
echo "- To force recreate all branches: $0 $EPIC_ID force"
echo "- To continue work on existing branches: $0 $EPIC_ID"