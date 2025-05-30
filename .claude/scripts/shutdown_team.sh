#!/bin/bash
# shutdown_team.sh - Gracefully shutdown all agents with branch cleanup options

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_REPO="/root/workspace/am-agents-labs"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${YELLOW}Shutting down all agents...${NC}"

# Stop all agent tmux sessions
shutdown_count=0
for agent in alpha beta delta epsilon gamma; do
    if tmux has-session -t "agent-$agent" 2>/dev/null; then
        echo "Stopping $agent..."
        tmux kill-session -t "agent-$agent"
        ((shutdown_count++))
    fi
done

if [[ $shutdown_count -eq 0 ]]; then
    echo -e "${YELLOW}No running agents found${NC}"
else
    echo -e "${GREEN}Stopped $shutdown_count agents${NC}"
fi

echo ""
echo "Would you like to clean up worktrees? (y/n)"
read -r response

if [[ "$response" == "y" ]]; then
    cd "$BASE_REPO"
    
    echo ""
    echo "How would you like to clean up?"
    echo "1) Remove worktrees only (keep branches)"
    echo "2) Remove worktrees and local branches"
    echo "3) Remove worktrees, local branches, and remote branches"
    echo ""
    read -p "Choose option (1-3): " cleanup_option
    
    worktrees=(
        "$BASE_REPO/../am-agents-core"
        "$BASE_REPO/../am-agents-api"
        "$BASE_REPO/../am-agents-tools"
        "$BASE_REPO/../am-agents-tests"
    )
    
    # First, remove worktrees
    for path in "${worktrees[@]}"; do
        if [[ -d "$path" ]]; then
            echo -e "${BLUE}Removing worktree: $path${NC}"
            
            # Get branch name before removing
            branch_name=$(cd "$path" && git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")
            
            # Remove worktree
            git worktree remove "$path" --force 2>/dev/null || {
                echo -e "${YELLOW}Warning: Could not remove $path${NC}"
            }
            
            # Handle branch cleanup based on option
            if [[ "$cleanup_option" == "2" ]] || [[ "$cleanup_option" == "3" ]]; then
                if [[ -n "$branch_name" ]] && git show-ref --verify --quiet "refs/heads/$branch_name"; then
                    echo -e "${BLUE}Deleting local branch: $branch_name${NC}"
                    git branch -D "$branch_name" 2>/dev/null || true
                fi
            fi
            
            if [[ "$cleanup_option" == "3" ]]; then
                if [[ -n "$branch_name" ]] && git ls-remote --heads origin "$branch_name" | grep -q "$branch_name"; then
                    echo -e "${RED}Deleting remote branch: origin/$branch_name${NC}"
                    git push origin --delete "$branch_name" 2>/dev/null || {
                        echo -e "${YELLOW}Warning: Could not delete remote branch${NC}"
                    }
                fi
            fi
        fi
    done
    
    # Prune worktree references
    git worktree prune
    echo -e "${GREEN}Worktree cleanup complete${NC}"
fi

echo ""
echo "Would you like to archive logs and sessions? (y/n)"
read -r response

if [[ "$response" == "y" ]]; then
    ARCHIVE_DIR="${SCRIPT_DIR}/../archives"
    mkdir -p "$ARCHIVE_DIR"
    
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    ARCHIVE_NAME="team_run_${TIMESTAMP}.tar.gz"
    
    cd "${SCRIPT_DIR}/.."
    tar -czf "$ARCHIVE_DIR/$ARCHIVE_NAME" logs/ sessions/
    
    echo -e "${GREEN}Logs and sessions archived to: archives/$ARCHIVE_NAME${NC}"
    
    echo "Clear current logs and sessions? (y/n)"
    read -r response
    
    if [[ "$response" == "y" ]]; then
        rm -f logs/*.log sessions/*.txt sessions/*.json
        echo -e "${GREEN}Current logs and sessions cleared${NC}"
    fi
fi

echo ""
echo -e "${GREEN}Shutdown complete!${NC}"
echo ""
echo "To start a new epic run:"
echo "  $SCRIPT_DIR/run_team.sh 'Epic Name' 123"
echo ""
echo "To reuse existing branches:"
echo "  REUSE_BRANCHES=true $SCRIPT_DIR/run_team.sh 'Epic Name' 123"