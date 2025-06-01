#!/bin/bash
# run_team.sh - Start Alpha orchestrator who manages the team

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Configuration - Updated paths for workspace root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROMPTS_DIR="${SCRIPT_DIR}/am-agents-labs/.claude/scripts/agents-prompts"
LOGS_DIR="${SCRIPT_DIR}/am-agents-labs/.claude/scripts/logs"
SESSIONS_DIR="${SCRIPT_DIR}/am-agents-labs/.claude/scripts/sessions"
AGENT_SCRIPTS_DIR="${SCRIPT_DIR}/am-agents-labs/.claude/scripts/agent-scripts"
BASE_REPO_DIR="${SCRIPT_DIR}/am-agents-labs"

# Epic configuration
EPIC_NAME="${1:-}"
EPIC_ID="${2:-}"
MAX_TURNS="${MAX_TURNS:-30}"
AGENT_TIMEOUT="${AGENT_TIMEOUT:-7200}" # 2 hours default
REUSE_BRANCHES="${REUSE_BRANCHES:-false}" # Default to creating fresh branches

# WhatsApp configuration
WHATSAPP_URL="http://192.168.112.142:8080/message/sendText/SofIA"
WHATSAPP_GROUP="120363404050997890@g.us"
WHATSAPP_KEY="namastex888"

# Ensure required directories exist
mkdir -p "$LOGS_DIR" "$SESSIONS_DIR"

# Function to print colored output
print_status() {
    local color=$1
    local agent=$2
    local message=$3
    echo -e "${color}[${agent}]${NC} ${message}"
}

# Function to send WhatsApp message
send_whatsapp() {
    local message="$1"
    # Create proper JSON payload without over-escaping
    local json_payload=$(jq -n --arg text "$message" --arg number "$WHATSAPP_GROUP" '{number: $number, text: $text}')
    
    local response=$(curl -s -X POST "$WHATSAPP_URL" \
        -H "Content-Type: application/json" \
        -H "apikey: $WHATSAPP_KEY" \
        -d "$json_payload" 2>&1)
    
    local exit_code=$?
    
    if [[ $exit_code -eq 0 ]] && [[ "$response" == *"PENDING"* || "$response" == *"SUCCESS"* ]]; then
        print_status "$GREEN" "WHATSAPP" "Message sent successfully"
    else
        print_status "$YELLOW" "WHATSAPP" "Warning: Message may have failed"
    fi
}

# Function to validate environment
validate_environment() {
    print_status "$BLUE" "SYSTEM" "Validating environment..."
    
    # Check if alpha prompt exists (only alpha needed initially)
    if [[ ! -f "$PROMPTS_DIR/alpha_prompt.md" ]]; then
        print_status "$RED" "ERROR" "Missing prompt file: alpha_prompt.md"
        exit 1
    fi
    
    # Check if base repo exists
    if [[ ! -d "$BASE_REPO_DIR" ]]; then
        print_status "$RED" "ERROR" "Base repository not found: $BASE_REPO_DIR"
        exit 1
    fi
    
    # Check if agent scripts exist
    if [[ ! -f "$AGENT_SCRIPTS_DIR/run_alpha.sh" ]]; then
        print_status "$RED" "ERROR" "Missing agent script: run_alpha.sh"
        exit 1
    fi
    
    print_status "$GREEN" "SYSTEM" "Environment validation passed"
}

# Function to setup worktrees for the epic
setup_epic_environment() {
    local epic_id=$1
    local force_flag=""
    
    if [[ "$REUSE_BRANCHES" != "true" ]]; then
        force_flag="force"
    fi
    
    print_status "$BLUE" "SETUP" "Setting up worktrees for epic NMSTX-${epic_id}..."
    
    if [[ -f "$SCRIPT_DIR/setup_worktrees.sh" ]]; then
        "$SCRIPT_DIR/setup_worktrees.sh" "$epic_id" "$force_flag"
    else
        print_status "$RED" "ERROR" "setup_worktrees.sh not found in workspace root"
        exit 1
    fi
}

# Function to cleanup background processes
cleanup() {
    print_status "$YELLOW" "CLEANUP" "Cleaning up background processes..."
    
    # Note: tmux sessions will continue running after script exits
    # Use 'shutdown_team.sh' to stop all agent sessions
    
    print_status "$GREEN" "CLEANUP" "Cleanup complete"
}

# Function to start agent in tmux session
start_agent_tmux() {
    local agent="$1"
    local task="$2"
    local session_name="agent-${agent}"
    
    # Kill existing session if it exists
    if tmux has-session -t "$session_name" 2>/dev/null; then
        print_status "$YELLOW" "$agent" "Killing existing tmux session"
        tmux kill-session -t "$session_name"
    fi
    
    # Create new tmux session
    print_status "$BLUE" "$agent" "Creating tmux session: $session_name"
    
    cd "$AGENT_SCRIPTS_DIR"
    tmux new-session -d -s "$session_name" -c "$AGENT_SCRIPTS_DIR"
    
    # Send the command to the session
    local cmd="MAX_TURNS=\"$MAX_TURNS\" ./run_${agent}.sh \"$task\""
    tmux send-keys -t "$session_name" "$cmd" Enter
    
    # Save tmux session info to a separate file (don't overwrite Claude session ID)
    echo "$session_name" > "$SESSIONS_DIR/${agent}_tmux.txt"
    
    print_status "$GREEN" "$agent" "Started in tmux session: $session_name"
    return 0
}

# Function to show monitoring commands
show_monitoring_commands() {
    local epic_name="$1"
    local epic_id="$2"
    
    echo ""
    print_status "$BLUE" "MONITORING" "=== Agent Team Monitoring Commands ==="
    echo ""
    
    print_status "$GREEN" "TMUX" "Control tmux sessions:"
    echo "  tmux list-sessions                   # List all sessions"
    echo "  tmux attach -t agent-alpha           # Attach to alpha session"
    echo "  tmux attach -t agent-beta            # Attach to beta session"
    echo "  tmux attach -t agent-delta           # Attach to delta session"
    echo "  tmux attach -t agent-epsilon         # Attach to epsilon session"
    echo "  tmux attach -t agent-gamma           # Attach to gamma session"
    echo "  # Press Ctrl+B then D to detach from tmux session"
    echo ""
    
    print_status "$GREEN" "LOGS" "View agent logs:"
    echo "  tail -f $LOGS_DIR/alpha_agent.log    # Alpha orchestrator"
    echo "  tail -f $LOGS_DIR/beta_agent.log     # Beta core builder"
    echo "  tail -f $LOGS_DIR/delta_agent.log    # Delta API builder"
    echo "  tail -f $LOGS_DIR/epsilon_agent.log  # Epsilon tool builder"
    echo "  tail -f $LOGS_DIR/gamma_agent.log    # Gamma quality engineer"
    echo ""
    
    print_status "$GREEN" "STATUS" "Check agent status:"
    echo "  $SCRIPT_DIR/monitor_agents.sh        # Quick status check"
    echo "  $SCRIPT_DIR/monitor_agents.sh watch  # Continuous monitoring"
    echo "  SEND_WHATSAPP=true $SCRIPT_DIR/monitor_agents.sh  # Status to WhatsApp"
    echo ""
    
    print_status "$GREEN" "CONTROL" "Team control:"
    echo "  $SCRIPT_DIR/shutdown_team.sh         # Stop all agents"
    echo "  tmux kill-session -t agent-<name>    # Stop specific agent"
    echo "  tmux kill-server                     # Stop all tmux sessions"
    echo ""
    
    print_status "$GREEN" "RESULTS" "Check epic progress:"
    echo "  Epic: $epic_name"
    echo "  ID: NMSTX-$epic_id"
    echo "  git status                           # Check repo changes"
    echo "  git log --oneline -10                # Recent commits"
    echo ""
    
    # Show current tmux sessions
    echo ""
    print_status "$BLUE" "TMUX" "Active tmux sessions:"
    if tmux list-sessions 2>/dev/null | grep -q "agent-"; then
        tmux list-sessions 2>/dev/null | grep "agent-" | while read line; do
            print_status "$GREEN" "SESSION" "$line"
        done
    else
        print_status "$YELLOW" "SESSION" "No agent sessions found"
    fi
    
    # Show current agent session files
    echo ""
    print_status "$BLUE" "FILES" "Session tracking files:"
    for agent in alpha beta delta epsilon gamma; do
        local claude_session_file="$SESSIONS_DIR/${agent}_session.txt"
        local tmux_session_file="$SESSIONS_DIR/${agent}_tmux.txt"
        
        if [[ -f "$claude_session_file" ]]; then
            local claude_session_id=$(cat "$claude_session_file")
            print_status "$GREEN" "$agent" "Claude session: $claude_session_id"
        else
            print_status "$YELLOW" "$agent" "No Claude session file"
        fi
        
        if [[ -f "$tmux_session_file" ]]; then
            local tmux_session_name=$(cat "$tmux_session_file")
            print_status "$GREEN" "$agent" "TMux session: $tmux_session_name"
        else
            print_status "$YELLOW" "$agent" "No tmux session file"
        fi
    done
}

# Set up signal handlers
trap cleanup EXIT INT TERM

# Main execution
main() {
    if [[ -z "$EPIC_NAME" ]] || [[ -z "$EPIC_ID" ]]; then
        echo "Usage: $0 <epic_name> <epic_id>"
        echo "Example: $0 'MCP Integration' 127"
        echo ""
        echo "Environment variables:"
        echo "  MAX_TURNS=30           # Maximum turns per agent"
        echo "  AGENT_TIMEOUT=7200     # Agent timeout in seconds"
        echo "  REUSE_BRANCHES=false   # Reuse existing branches"
        exit 1
    fi
    
    print_status "$PURPLE" "TEAM" "Starting automagik agents team..."
    print_status "$BLUE" "EPIC" "Epic: $EPIC_NAME (NMSTX-$EPIC_ID)"
    
    # Validate environment
    validate_environment
    
    # Setup epic environment (worktrees and branches)
    setup_epic_environment "$EPIC_ID"
    
    # Send team start notification
    START_MSG="🚀 *Automagik Agents Team Started*

📋 Epic: $EPIC_NAME
🆔 ID: NMSTX-$EPIC_ID
⏰ Time: $(date)
🔧 Max Turns: $MAX_TURNS
⚙️ Timeout: ${AGENT_TIMEOUT}s

🤖 *Team Formation:*
• Alpha: Orchestrator (main repo)
• Beta: Core Builder
• Delta: API Builder
• Epsilon: Tool Builder
• Gamma: Quality Engineer

_Alpha will coordinate the team to complete this epic._"
    
    send_whatsapp "$START_MSG"
    
    # Start Alpha orchestrator in tmux session
    print_status "$PURPLE" "ALPHA" "Starting Alpha orchestrator in tmux session..."
    
    local alpha_task="Epic: $EPIC_NAME (NMSTX-$EPIC_ID) - Coordinate the team to complete this epic. Set up the worktrees, assign tasks to team members, and orchestrate the development process."
    
    # Start alpha in tmux session
    start_agent_tmux "alpha" "$alpha_task"
    
    # Give alpha a moment to initialize
    sleep 3
    
    print_status "$GREEN" "ALPHA" "Alpha orchestrator started in tmux session: agent-alpha"
    print_status "$BLUE" "TEAM" "Team deployment complete - agents running in tmux sessions"
    
    # Show monitoring commands
    show_monitoring_commands "$EPIC_NAME" "$EPIC_ID"
    
    print_status "$GREEN" "SUCCESS" "Team started successfully! Use the commands above to monitor progress."
    print_status "$BLUE" "TMUX" "Main command: tmux attach -t agent-alpha (to watch alpha orchestrator)"
    
    return 0
}

main "$@" 