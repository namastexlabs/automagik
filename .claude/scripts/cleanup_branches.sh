#!/bin/bash
# cleanup_branches.sh - Utility to clean up epic branches

set -euo pipefail

BASE_REPO="/root/workspace/am-agents-labs"
EPIC_ID="${1:-}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

if [[ -z "$EPIC_ID" ]]; then
    echo "Usage: $0 <epic_id|all>"
    echo "Example: $0 127        # Clean branches for epic 127"
    echo "Example: $0 all        # Clean all NMSTX branches"
    exit 1
fi

cd "$BASE_REPO"

echo -e "${BLUE}Fetching latest from origin...${NC}"
git fetch origin --prune

if [[ "$EPIC_ID" == "all" ]]; then
    pattern="NMSTX-*"
    echo -e "${YELLOW}Finding all NMSTX branches...${NC}"
else
    pattern="NMSTX-${EPIC_ID}-*"
    echo -e "${YELLOW}Finding branches for epic NMSTX-${EPIC_ID}...${NC}"
fi

# Find local branches
local_branches=$(git branch | grep "$pattern" | sed 's/^[* ]*//' || true)
remote_branches=$(git branch -r | grep "origin/$pattern" | sed 's/^[* ]*origin\///' || true)

echo ""
echo -e "${BLUE}Local branches found:${NC}"
if [[ -z "$local_branches" ]]; then
    echo "  None"
else
    echo "$local_branches" | sed 's/^/  /'
fi

echo ""
echo -e "${BLUE}Remote branches found:${NC}"
if [[ -z "$remote_branches" ]]; then
    echo "  None"
else
    echo "$remote_branches" | sed 's/^/  origin\//'
fi

if [[ -z "$local_branches" ]] && [[ -z "$remote_branches" ]]; then
    echo ""
    echo -e "${GREEN}No branches to clean up${NC}"
    exit 0
fi

echo ""
echo -e "${YELLOW}What would you like to do?${NC}"
echo "1) Delete local branches only"
echo "2) Delete remote branches only"
echo "3) Delete both local and remote branches"
echo "4) Cancel"
read -p "Choose option (1-4): " option

case $option in
    1|3)
        if [[ -n "$local_branches" ]]; then
            echo ""
            echo -e "${RED}Deleting local branches...${NC}"
            echo "$local_branches" | while read -r branch; do
                echo "  Deleting: $branch"
                git branch -D "$branch" 2>/dev/null || echo "    Failed to delete $branch"
            done
        fi
        ;;&
    2|3)
        if [[ -n "$remote_branches" ]]; then
            echo ""
            echo -e "${RED}Deleting remote branches...${NC}"
            echo "$remote_branches" | while read -r branch; do
                echo "  Deleting: origin/$branch"
                git push origin --delete "$branch" 2>/dev/null || echo "    Failed to delete origin/$branch"
            done
        fi
        ;;
    4)
        echo -e "${YELLOW}Cancelled${NC}"
        exit 0
        ;;
    *)
        echo -e "${RED}Invalid option${NC}"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}Branch cleanup complete!${NC}"

# Clean up any stale worktree references
echo -e "${BLUE}Pruning worktree references...${NC}"
git worktree prune

echo -e "${GREEN}Done!${NC}"