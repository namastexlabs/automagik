#!/bin/bash
# monitor_agents.sh - Monitor all running agents

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOGS_DIR="${SCRIPT_DIR}/../logs"
SESSIONS_DIR="${SCRIPT_DIR}/../sessions"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
PURPLE='\033[0;35m'
NC='\033[0m'

# Agent colors mapping
declare -A AGENT_COLORS=(
    ["alpha"]="$PURPLE"
    ["beta"]="$GREEN"
    ["delta"]="$BLUE"
    ["epsilon"]="$YELLOW"
    ["gamma"]="$RED"
)

# Function to get latest log file for agent
get_latest_log() {
    local agent=$1
    ls -t "$LOGS_DIR/${agent}_"*.log 2>/dev/null | head -1
}

# Function to check agent status
check_agent_status() {
    local agent=$1
    local color=${AGENT_COLORS[$agent]}
    
    echo -e "${color}━━━ $agent ━━━${NC}"
    
    # Check tmux session
    if tmux has-session -t "agent-$agent" 2>/dev/null; then
        echo -e "Status: ${GREEN}Running${NC}"
        
        # Show session info
        if [[ -f "$SESSIONS_DIR/${agent}_session.txt" ]]; then
            local session_id=$(cat "$SESSIONS_DIR/${agent}_session.txt")
            echo "Session: $session_id"
        fi
        
        # Show recent activity
        local log_file=$(get_latest_log "$agent")
        if [[ -n "$log_file" ]]; then
            echo "Recent activity:"
            tail -5 "$log_file" | sed 's/^/  /'
        fi
    else
        echo -e "Status: ${RED}Not running${NC}"
    fi
    
    echo ""
}

# Function to show memory coordination
show_memory_coordination() {
    echo -e "${BLUE}━━━ Recent Memory Coordination ━━━${NC}"
    
    # Search for coordination messages in recent logs
    if ls "$LOGS_DIR"/*.log 1> /dev/null 2>&1; then
        echo "Recent handoffs and status updates:"
        grep -h "\[C-HANDOFF\]\|\[C-READY\]\|\[P-TASK\]\|\[C-BLOCKED\]" "$LOGS_DIR"/*.log 2>/dev/null | tail -10 | sed 's/^/  /'
    else
        echo "  No coordination messages found yet"
    fi
    
    echo ""
}

# Main monitoring loop
main() {
    clear
    
    while true; do
        echo -e "${BLUE}═══════════════════════════════════════${NC}"
        echo -e "${BLUE}     Multi-Agent Team Monitor${NC}"
        echo -e "${BLUE}═══════════════════════════════════════${NC}"
        echo "Time: $(date)"
        echo ""
        
        # Check each agent
        for agent in alpha beta delta epsilon gamma; do
            check_agent_status "$agent"
        done
        
        # Show coordination status
        show_memory_coordination
        
        echo "Controls:"
        echo "  - Attach to agent: tmux attach -t agent-<name>"
        echo "  - View full log: tail -f $LOGS_DIR/<agent>_*.log"
        echo "  - Continue agent: ./run_agent.sh <agent> --continue"
        echo "  - Quit monitor: Ctrl+C"
        echo ""
        echo "Refreshing in 10 seconds..."
        
        sleep 10
        clear
    done
}

# Handle Ctrl+C gracefully
trap 'echo -e "\n${GREEN}Monitor stopped${NC}"; exit 0' INT

# Run main
main