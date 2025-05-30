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
# The '+' prefix indicates branches with worktrees
# We need to strip both '* ' (current branch) and '+ ' (worktree branches)
local_branches=$(git branch | grep "$pattern" | sed 's/^[*+ ]*//' | grep -v "^$" || true)
remote_branches=$(git branch -r | grep "origin/$pattern" | sed 's/^[* ]*origin\///' | grep -v "^$" || true)

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

# Check for worktrees before offering to delete
worktree_branches=$(git worktree list --porcelain | grep "^branch " | sed 's/^branch refs\/heads\///' | grep "$pattern" || true)
if [[ -n "$worktree_branches" ]]; then
    echo ""
    echo -e "${YELLOW}WARNING: The following branches have active worktrees:${NC}"
    echo "$worktree_branches" | sed 's/^/  /'
    echo ""
    echo -e "${YELLOW}You should remove worktrees first with:${NC}"
    echo "  git worktree remove <path>"
    echo "  OR"
    echo "  ./shutdown_team.sh"
    echo ""
    read -p "Continue anyway? (y/n): " continue_anyway
    if [[ "$continue_anyway" != "y" ]]; then
        echo -e "${YELLOW}Cancelled${NC}"
        exit 0
    fi
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
            echo "$local_branches" | while IFS= read -r branch; do
                # Trim any whitespace
                branch=$(echo "$branch" | xargs)
                if [[ -n "$branch" ]]; then
                    echo "  Deleting: $branch"
                    if git branch -D "$branch" 2>/dev/null; then
                        echo -e "    ${GREEN}✓ Deleted successfully${NC}"
                    else
                        # If deletion fails, try to remove worktree first
                        echo -e "    ${YELLOW}Failed - checking for worktree...${NC}"
                        worktree_path=$(git worktree list | grep "$branch" | awk '{print $1}' || true)
                        if [[ -n "$worktree_path" ]]; then
                            echo "    Removing worktree at: $worktree_path"
                            git worktree remove "$worktree_path" --force 2>/dev/null || true
                            # Try to delete branch again
                            if git branch -D "$branch" 2>/dev/null; then
                                echo -e "    ${GREEN}✓ Deleted after removing worktree${NC}"
                            else
                                echo -e "    ${RED}✗ Still failed to delete${NC}"
                            fi
                        else
                            echo -e "    ${RED}✗ Failed to delete (may be checked out)${NC}"
                        fi
                    fi
                fi
            done
        fi
        ;;&  # Continue to next case if 3 was selected
    2|3)
        if [[ -n "$remote_branches" ]]; then
            echo ""
            echo -e "${RED}Deleting remote branches...${NC}"
            echo "$remote_branches" | while IFS= read -r branch; do
                # Trim any whitespace
                branch=$(echo "$branch" | xargs)
                if [[ -n "$branch" ]]; then
                    echo "  Deleting: origin/$branch"
                    if git push origin --delete "$branch" 2>/dev/null; then
                        echo -e "    ${GREEN}✓ Deleted successfully${NC}"
                    else
                        echo -e "    ${RED}✗ Failed to delete${NC}"
                    fi
                fi
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

# Show remaining branches
remaining_local=$(git branch | grep "$pattern" | sed 's/^[*+ ]*//' || true)
if [[ -n "$remaining_local" ]]; then
    echo ""
    echo -e "${YELLOW}Remaining local branches:${NC}"
    echo "$remaining_local" | sed 's/^/  /'
fi

echo ""
echo -e "${GREEN}Done!${NC}"