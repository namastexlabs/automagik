#!/bin/bash
# run_team.sh - Main orchestration script for 5-agent team

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
PROMPTS_DIR="${SCRIPT_DIR}/agents_prompts"
LOGS_DIR="${SCRIPT_DIR}/logs"
SESSIONS_DIR="${SCRIPT_DIR}/sessions"
BASE_REPO_DIR="/root/workspace/am-agents-labs"

# Epic configuration
EPIC_NAME="${1:-}"
EPIC_ID="${2:-}"
MAX_TURNS="${MAX_TURNS:-30}"
AGENT_TIMEOUT="${AGENT_TIMEOUT:-7200}" # 2 hours default

# Ensure required directories exist
mkdir -p "$LOGS_DIR" "$SESSIONS_DIR"

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
    
    # Check if prompts exist
    for agent in alpha beta delta epsilon gamma; do
        if [[ ! -f "$PROMPTS_DIR/${agent}.md" ]]; then
            print_status "$RED" "ERROR" "Missing prompt file: ${agent}.md"
            exit 1
        fi
    done
    
    # Check if base repo exists
    if [[ ! -d "$BASE_REPO_DIR" ]]; then
        print_status "$RED" "ERROR" "Base repository not found: $BASE_REPO_DIR"
        exit 1
    fi
    
    # Check if claude is available
    if ! command -v claude &> /dev/null; then
        print_status "$RED" "ERROR" "Claude CLI not found in PATH"
        exit 1
    fi
    
    print_status "$GREEN" "SYSTEM" "Environment validation complete"
}

# Function to setup worktrees
setup_worktrees() {
    print_status "$BLUE" "SYSTEM" "Setting up worktrees for epic: $EPIC_NAME"
    
    cd "$BASE_REPO_DIR"
    
    # Create worktrees for each agent (except Alpha who uses main)
    local branches=(
        "beta:core:$BASE_REPO_DIR/../am-agents-core"
        "delta:api:$BASE_REPO_DIR/../am-agents-api"
        "epsilon:tools:$BASE_REPO_DIR/../am-agents-tools"
        "gamma:tests:$BASE_REPO_DIR/../am-agents-tests"
    )
    
    for branch_info in "${branches[@]}"; do
        IFS=':' read -r agent component path <<< "$branch_info"
        branch_name="NMSTX-${EPIC_ID}-${component}"
        
        if [[ -d "$path" ]]; then
            print_status "$YELLOW" "$agent" "Worktree already exists at $path"
        else
            print_status "$BLUE" "$agent" "Creating worktree: $branch_name"
            git worktree add "$path" -b "$branch_name" || {
                print_status "$RED" "$agent" "Failed to create worktree"
                exit 1
            }
        fi
    done
    
    print_status "$GREEN" "SYSTEM" "Worktrees setup complete"
}

# Function to create initial epic context
create_epic_context() {
    cat > "$SESSIONS_DIR/epic_context.txt" << EOF
Epic: $EPIC_NAME
Linear ID: NMSTX-${EPIC_ID}
Start Time: $(date)
Team Members: Alpha (Orchestrator), Beta (Core), Delta (API), Epsilon (Tools), Gamma (Quality)

Initial Task: Break down the epic into parallel work streams and coordinate the team to deliver within 24 hours.
EOF
}

# Function to start an agent
start_agent() {
    local agent_name=$1
    local agent_color=$2
    local work_dir=$3
    local initial_prompt=$4
    
    local prompt_file="$PROMPTS_DIR/${agent_name}.md"
    local log_file="$LOGS_DIR/${agent_name}_$(date +%Y%m%d_%H%M%S).log"
    local session_file="$SESSIONS_DIR/${agent_name}_session.txt"
    
    print_status "$agent_color" "$agent_name" "Starting agent..."
    
    # Create agent startup script
    cat > "$SESSIONS_DIR/start_${agent_name}.sh" << EOF
#!/bin/bash
cd "$work_dir"
export AGENT_NAME="$agent_name"
export EPIC_NAME="$EPIC_NAME"
export EPIC_ID="$EPIC_ID"

# Read system prompt
SYSTEM_PROMPT=\$(cat "$prompt_file")

# Start Claude with the prompt
if [[ -z "$initial_prompt" ]]; then
    # No initial prompt, just system prompt
    claude --append-system-prompt "\$SYSTEM_PROMPT" \\
           --max-turns $MAX_TURNS \\
           --output-format json \\
           2>&1 | tee "$log_file" | \\
           jq -r '.session_id' > "$session_file"
else
    # With initial prompt
    claude -p "$initial_prompt" \\
           --append-system-prompt "\$SYSTEM_PROMPT" \\
           --max-turns $MAX_TURNS \\
           --output-format json \\
           2>&1 | tee "$log_file" | \\
           jq -r '.session_id' > "$session_file"
fi
EOF
    
    chmod +x "$SESSIONS_DIR/start_${agent_name}.sh"
    
    # Start agent in tmux session
    tmux new-session -d -s "agent-$agent_name" \
        "timeout $AGENT_TIMEOUT $SESSIONS_DIR/start_${agent_name}.sh"
    
    print_status "$GREEN" "$agent_name" "Agent started in tmux session: agent-$agent_name"
}

# Function to start all agents
start_all_agents() {
    print_status "$BLUE" "SYSTEM" "Starting all agents..."
    
    # Alpha starts with epic context
    start_agent "alpha" "$PURPLE" "$BASE_REPO_DIR" \
        "Analyze this epic and coordinate the team: $(cat $SESSIONS_DIR/epic_context.txt)"
    
    # Wait for Alpha to create initial plan
    sleep 10
    
    # Start builders in parallel (they wait for Alpha's handoff)
    start_agent "beta" "$GREEN" "$BASE_REPO_DIR/../am-agents-core" \
        "Wait for task assignment from Alpha, then implement core features for epic NMSTX-${EPIC_ID}"
    
    start_agent "delta" "$BLUE" "$BASE_REPO_DIR/../am-agents-api" \
        "Wait for task assignment from Alpha, then implement API endpoints for epic NMSTX-${EPIC_ID}"
    
    start_agent "epsilon" "$YELLOW" "$BASE_REPO_DIR/../am-agents-tools" \
        "Wait for task assignment from Alpha, then implement tool integrations for epic NMSTX-${EPIC_ID}"
    
    # Gamma starts immediately to prepare tests
    start_agent "gamma" "$RED" "$BASE_REPO_DIR/../am-agents-tests" \
        "Prepare test structure for epic NMSTX-${EPIC_ID} while waiting for components from other agents"
}

# Function to show agent status
show_status() {
    print_status "$BLUE" "SYSTEM" "Agent Status:"
    echo "----------------------------------------"
    
    for agent in alpha beta delta epsilon gamma; do
        if tmux has-session -t "agent-$agent" 2>/dev/null; then
            echo -e "${GREEN}✓${NC} $agent: Running"
        else
            echo -e "${RED}✗${NC} $agent: Not running"
        fi
    done
    
    echo "----------------------------------------"
    echo "View logs: tail -f $LOGS_DIR/<agent>_*.log"
    echo "Attach to agent: tmux attach -t agent-<name>"
    echo "Monitor all: $SCRIPT_DIR/monitor_agents.sh"
}

# Main execution
main() {
    if [[ -z "$EPIC_NAME" ]] || [[ -z "$EPIC_ID" ]]; then
        echo "Usage: $0 <epic_name> <epic_id>"
        echo "Example: $0 'MCP Integration' 127"
        exit 1
    }
    
    print_status "$PURPLE" "SYSTEM" "Starting Multi-Agent Team for Epic: $EPIC_NAME"
    
    validate_environment
    setup_worktrees
    create_epic_context
    start_all_agents
    
    sleep 5
    show_status
    
    print_status "$GREEN" "SYSTEM" "Team started successfully!"
    print_status "$BLUE" "SYSTEM" "Monitor progress with: $SCRIPT_DIR/monitor_agents.sh"
}

# Run main
main