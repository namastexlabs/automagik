#!/bin/bash
# shutdown_team.sh - Gracefully shutdown all agents

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_REPO="/root/workspace/am-agents-labs"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
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
    
    worktrees=(
        "$BASE_REPO/../am-agents-core"
        "$BASE_REPO/../am-agents-api"
        "$BASE_REPO/../am-agents-tools"
        "$BASE_REPO/../am-agents-tests"
    )
    
    for path in "${worktrees[@]}"; do
        if [[ -d "$path" ]]; then
            echo "Removing worktree: $path"
            git worktree remove "$path" --force 2>/dev/null || {
                echo -e "${YELLOW}Warning: Could not remove $path${NC}"
            }
        fi
    done
    
    # Prune worktree references
    git worktree prune
    echo -e "${GREEN}Worktrees cleaned up${NC}"
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