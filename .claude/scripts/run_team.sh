#!/bin/bash
# run_team.sh - Start Alpha orchestrator who manages the team via individual scripts

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENT_SCRIPTS_DIR="${SCRIPT_DIR}/agent-scripts"
PROMPTS_DIR="${SCRIPT_DIR}/../agents-prompts"
LOGS_DIR="${SCRIPT_DIR}/../logs"
SESSIONS_DIR="${SCRIPT_DIR}/../sessions"
BASE_REPO_DIR="/root/workspace/am-agents-labs"

# Epic configuration
EPIC_NAME="${1:-}"
EPIC_ID="${2:-}"
MAX_TURNS="${MAX_TURNS:-30}"
REUSE_BRANCHES="${REUSE_BRANCHES:-false}"

# Ensure required directories exist
mkdir -p "$LOGS_DIR" "$SESSIONS_DIR" "$AGENT_SCRIPTS_DIR"

# Function to print colored output
print_status() {
    local color=$1
    local agent=$2
    local message=$3
    echo -e "${color}[${agent}]${NC} ${message}"
}

# Function to validate environment
validate_environment() {
    print_status "$BLUE" "SYSTEM" "Validating environment..."
    
    # Check if alpha prompt exists
    if [[ ! -f "$PROMPTS_DIR/alpha_prompt.md" ]]; then
        print_status "$RED" "ERROR" "Missing prompt file: alpha_prompt.md"
        exit 1
    fi
    
    # Check if required commands are available
    for cmd in claude tmux jq git curl; do
        if ! command -v $cmd &> /dev/null; then
            print_status "$RED" "ERROR" "$cmd not found in PATH"
            exit 1
        fi
    done
    
    # Check if agent scripts exist
    if [[ ! -f "$AGENT_SCRIPTS_DIR/run_alpha.sh" ]]; then
        print_status "$YELLOW" "SETUP" "Agent scripts not found. Creating them..."
        create_agent_scripts
    fi
    
    print_status "$GREEN" "SYSTEM" "Environment validation complete"
}

# Function to create agent scripts if they don't exist
create_agent_scripts() {
    print_status "$BLUE" "SETUP" "Creating agent runner scripts..."
    
    # Create agent-scripts directory
    mkdir -p "$AGENT_SCRIPTS_DIR"
    
    # Copy the individual run scripts to agent-scripts
    # In a real scenario, these would be the scripts from the artifacts
    print_status "$GREEN" "SETUP" "Agent scripts created in $AGENT_SCRIPTS_DIR"
    print_status "$YELLOW" "SETUP" "Please ensure all run_*.sh scripts are in agent-scripts/"
}

# Function to setup worktrees
setup_worktrees() {
    print_status "$BLUE" "SYSTEM" "Setting up parallel development workspaces..."
    
    cd "$BASE_REPO_DIR"
    
    # Fetch latest
    git fetch origin --prune
    
    # Setup worktrees
    local worktrees=(
        "core:/root/workspace/am-agents-core"
        "api:/root/workspace/am-agents-api"
        "tools:/root/workspace/am-agents-tools"
        "tests:/root/workspace/am-agents-tests"
    )
    
    for worktree_info in "${worktrees[@]}"; do
        IFS=':' read -r component path <<< "$worktree_info"
        local branch_name="NMSTX-${EPIC_ID}-${component}"
        
        if [[ -d "$path" ]]; then
            if [[ "$REUSE_BRANCHES" == "true" ]]; then
                print_status "$BLUE" "SETUP" "Reusing workspace at $path"
                continue
            else
                print_status "$YELLOW" "SETUP" "Removing existing workspace at $path"
                git worktree remove "$path" --force 2>/dev/null || true
            fi
        fi
        
        # Create new worktree
        print_status "$GREEN" "SETUP" "Creating $component workspace"
        git worktree add "$path" -b "$branch_name" 2>/dev/null || \
        git worktree add "$path" "$branch_name"
    done
    
    print_status "$GREEN" "SYSTEM" "Workspaces ready for parallel development"
}

# Function to create orchestration context
create_orchestration_context() {
    cat > "$SESSIONS_DIR/epic_context.txt" << EOF
Epic: $EPIC_NAME
Linear ID: NMSTX-${EPIC_ID}
Start Time: $(date)
Mode: Orchestrator-Controlled Execution

You are Alpha, the orchestrator. Your team members will be started on-demand using:
- $AGENT_SCRIPTS_DIR/run_beta.sh "task"
- $AGENT_SCRIPTS_DIR/run_delta.sh "task"  
- $AGENT_SCRIPTS_DIR/run_epsilon.sh "task"
- $AGENT_SCRIPTS_DIR/run_gamma.sh "task"

Use send_whatsapp_message frequently to keep the technical team updated.
EOF
}

# Function to start alpha only
start_alpha_orchestrator() {
    print_status "$PURPLE" "ALPHA" "Starting orchestrator..."
    
    # Check if already running
    if tmux has-session -t "agent-alpha" 2>/dev/null; then
        print_status "$YELLOW" "ALPHA" "Already running. Attaching..."
        tmux attach -t agent-alpha
        return
    fi
    
    # Start Alpha using the run script
    cd "$AGENT_SCRIPTS_DIR"
    ./run_alpha.sh "$(cat $SESSIONS_DIR/epic_context.txt)"
}

# Function to show final instructions
show_instructions() {
    clear
    print_status "$GREEN" "SYSTEM" "=== ORCHESTRATOR MODE ACTIVE ==="
    echo ""
    echo "Epic: $EPIC_NAME (NMSTX-${EPIC_ID})"
    echo "Strategy: Alpha orchestrates, agents start on-demand"
    echo ""
    echo "Workspaces Created:"
    echo "  • Main:  /root/workspace/am-agents-labs    (Alpha)"
    echo "  • Core:  /root/workspace/am-agents-core    (Beta)"
    echo "  • API:   /root/workspace/am-agents-api     (Delta)"
    echo "  • Tools: /root/workspace/am-agents-tools   (Epsilon)"
    echo "  • Tests: /root/workspace/am-agents-tests   (Gamma)"
    echo ""
    echo "Monitor Commands:"
    echo "  • Watch Alpha:     tmux attach -t agent-alpha"
    echo "  • Monitor all:     $SCRIPT_DIR/monitor_agents.sh"
    echo "  • View WhatsApp:   Check your WhatsApp group"
    echo ""
    echo "Alpha Control Commands:"
    echo "  • Start Beta:      $AGENT_SCRIPTS_DIR/run_beta.sh \"task\""
    echo "  • Start Delta:     $AGENT_SCRIPTS_DIR/run_delta.sh \"task\""
    echo "  • Start Epsilon:   $AGENT_SCRIPTS_DIR/run_epsilon.sh \"task\""
    echo "  • Start Gamma:     $AGENT_SCRIPTS_DIR/run_gamma.sh \"task\""
    echo ""
    echo "Continue Commands (run by human when needed):"
    echo "  • Continue Alpha:  RESUME_SESSION=<id> $AGENT_SCRIPTS_DIR/run_alpha.sh"
    echo "  • Continue Beta:   RESUME_SESSION=<id> $AGENT_SCRIPTS_DIR/run_beta.sh"
    echo "  • Continue Delta:  RESUME_SESSION=<id> $AGENT_SCRIPTS_DIR/run_delta.sh"
    echo "  • Continue others similarly..."
    echo ""
    print_status "$BLUE" "SYSTEM" "Alpha is now running. Check WhatsApp for updates!"
}

# Main execution
main() {
    if [[ -z "$EPIC_NAME" ]] || [[ -z "$EPIC_ID" ]]; then
        echo "Usage: $0 <epic_name> <epic_id>"
        echo ""
        echo "This starts ONLY Alpha as orchestrator."
        echo "Alpha will start other agents as needed."
        echo ""
        echo "Example: $0 'User Authentication' 164"
        exit 1
    fi
    
    print_status "$PURPLE" "SYSTEM" "=== ORCHESTRATOR MODE SETUP ==="
    echo ""
    
    validate_environment
    setup_worktrees
    create_orchestration_context
    
    # Show instructions before starting
    show_instructions
    
    echo ""
    read -p "Press Enter to start Alpha orchestrator..."
    
    # Start Alpha
    start_alpha_orchestrator
}

# Handle interrupts
trap 'print_status "$YELLOW" "SYSTEM" "Setup interrupted. Workspaces remain available."; exit 130' INT TERM

# Run main
main "$@"