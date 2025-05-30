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
PROMPTS_DIR="${SCRIPT_DIR}/../agents_prompts"
LOGS_DIR="${SCRIPT_DIR}/../logs"
SESSIONS_DIR="${SCRIPT_DIR}/../sessions"
BASE_REPO_DIR="/root/workspace/am-agents-labs"

# Epic configuration
EPIC_NAME="${1:-}"
EPIC_ID="${2:-}"
MAX_TURNS="${MAX_TURNS:-30}"
AGENT_TIMEOUT="${AGENT_TIMEOUT:-7200}" # 2 hours default
REUSE_BRANCHES="${REUSE_BRANCHES:-false}" # Default to creating fresh branches

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
    
    # Check if tmux is available
    if ! command -v tmux &> /dev/null; then
        print_status "$RED" "ERROR" "tmux not found in PATH"
        exit 1
    fi
    
    # Check if jq is available
    if ! command -v jq &> /dev/null; then
        print_status "$RED" "ERROR" "jq not found in PATH"
        exit 1
    fi
    
    print_status "$GREEN" "SYSTEM" "Environment validation complete"
}

# Function to setup a single worktree with proper branch handling
setup_single_worktree() {
    local agent=$1
    local component=$2
    local path=$3
    local branch_name="NMSTX-${EPIC_ID}-${component}"
    
    print_status "$BLUE" "$agent" "Setting up worktree for $component..."
    
    # Check if worktree already exists
    if [[ -d "$path" ]]; then
        local current_branch=$(cd "$path" && git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
        print_status "$YELLOW" "$agent" "Worktree exists at $path (branch: $current_branch)"
        
        if [[ "$current_branch" == "$branch_name" ]] && [[ "$REUSE_BRANCHES" == "true" ]]; then
            print_status "$GREEN" "$agent" "Reusing existing worktree on branch $branch_name"
            # Pull latest changes
            (cd "$path" && git pull origin main --rebase 2>/dev/null || true)
            return 0
        else
            print_status "$YELLOW" "$agent" "Removing existing worktree..."
            git worktree remove "$path" --force 2>/dev/null || true
        fi
    fi
    
    # Check if branch exists locally
    if git show-ref --verify --quiet "refs/heads/$branch_name"; then
        print_status "$YELLOW" "$agent" "Branch $branch_name exists locally"
        
        if [[ "$REUSE_BRANCHES" == "true" ]]; then
            print_status "$BLUE" "$agent" "Reusing existing branch"
            git worktree add "$path" "$branch_name"
        else
            print_status "$YELLOW" "$agent" "Deleting old branch and creating fresh"
            git branch -D "$branch_name" 2>/dev/null || true
            git worktree add "$path" -b "$branch_name"
        fi
    # Check if branch exists remotely
    elif git ls-remote --heads origin "$branch_name" | grep -q "$branch_name"; then
        print_status "$YELLOW" "$agent" "Branch exists on remote"
        
        if [[ "$REUSE_BRANCHES" == "true" ]]; then
            print_status "$BLUE" "$agent" "Checking out remote branch"
            git worktree add "$path" -b "$branch_name" "origin/$branch_name" 2>/dev/null || \
            git worktree add "$path" "$branch_name"
        else
            print_status "$YELLOW" "$agent" "Creating fresh branch (ignoring remote)"
            git worktree add "$path" -b "$branch_name"
        fi
    else
        # Create new branch
        print_status "$GREEN" "$agent" "Creating new branch: $branch_name"
        git worktree add "$path" -b "$branch_name"
    fi
    
    # Ensure worktree has latest changes from main
    print_status "$BLUE" "$agent" "Syncing with main branch..."
    (cd "$path" && git pull origin main --rebase 2>/dev/null || true)
    
    print_status "$GREEN" "$agent" "Worktree ready at $path"
}

# Function to setup worktrees
setup_worktrees() {
    print_status "$BLUE" "SYSTEM" "Setting up worktrees for epic: $EPIC_NAME"
    
    cd "$BASE_REPO_DIR"
    
    # First, fetch latest from origin
    print_status "$BLUE" "SYSTEM" "Fetching latest from origin..."
    git fetch origin --prune
    
    # Setup worktrees for each agent (except Alpha who uses main)
    local worktrees=(
        "beta:core:$BASE_REPO_DIR/../am-agents-core"
        "delta:api:$BASE_REPO_DIR/../am-agents-api"
        "epsilon:tools:$BASE_REPO_DIR/../am-agents-tools"
        "gamma:tests:$BASE_REPO_DIR/../am-agents-tests"
    )
    
    for worktree_info in "${worktrees[@]}"; do
        IFS=':' read -r agent component path <<< "$worktree_info"
        setup_single_worktree "$agent" "$component" "$path"
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
Branch Mode: ${REUSE_BRANCHES}

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
    
    # Check if agent is already running
    if tmux has-session -t "agent-$agent_name" 2>/dev/null; then
        print_status "$YELLOW" "$agent_name" "Agent already running in tmux session"
        print_status "$YELLOW" "$agent_name" "Killing existing session..."
        tmux kill-session -t "agent-$agent_name"
        sleep 2
    fi
    
    # Create agent startup script
    cat > "$SESSIONS_DIR/start_${agent_name}.sh" << 'AGENT_SCRIPT'
#!/bin/bash
cd "WORK_DIR_PLACEHOLDER"
export AGENT_NAME="AGENT_NAME_PLACEHOLDER"
export EPIC_NAME="EPIC_NAME_PLACEHOLDER"
export EPIC_ID="EPIC_ID_PLACEHOLDER"

# Read system prompt
SYSTEM_PROMPT=$(cat "PROMPT_FILE_PLACEHOLDER")

# Start Claude with the prompt
if [[ -z "INITIAL_PROMPT_PLACEHOLDER" ]]; then
    # No initial prompt, just system prompt
    OUTPUT=$(claude --append-system-prompt "$SYSTEM_PROMPT" \
           --max-turns MAX_TURNS_PLACEHOLDER \
           --output-format json 2>&1 | tee "LOG_FILE_PLACEHOLDER")
else
    # With initial prompt
    OUTPUT=$(claude -p "INITIAL_PROMPT_PLACEHOLDER" \
           --append-system-prompt "$SYSTEM_PROMPT" \
           --max-turns MAX_TURNS_PLACEHOLDER \
           --output-format json 2>&1 | tee "LOG_FILE_PLACEHOLDER")
fi

# Extract and save session ID
echo "$OUTPUT" | jq -r '.session_id // empty' > "SESSION_FILE_PLACEHOLDER"

# If no session ID found, try to extract from logs
if [[ ! -s "SESSION_FILE_PLACEHOLDER" ]]; then
    # Sometimes session ID appears in different formats
    grep -oP 'session[_-]?id["\s:]+\K[a-zA-Z0-9-]+' "LOG_FILE_PLACEHOLDER" | head -1 > "SESSION_FILE_PLACEHOLDER"
fi
AGENT_SCRIPT
    
    # Replace placeholders
    sed -i "s|WORK_DIR_PLACEHOLDER|$work_dir|g" "$SESSIONS_DIR/start_${agent_name}.sh"
    sed -i "s|AGENT_NAME_PLACEHOLDER|$agent_name|g" "$SESSIONS_DIR/start_${agent_name}.sh"
    sed -i "s|EPIC_NAME_PLACEHOLDER|$EPIC_NAME|g" "$SESSIONS_DIR/start_${agent_name}.sh"
    sed -i "s|EPIC_ID_PLACEHOLDER|$EPIC_ID|g" "$SESSIONS_DIR/start_${agent_name}.sh"
    sed -i "s|PROMPT_FILE_PLACEHOLDER|$prompt_file|g" "$SESSIONS_DIR/start_${agent_name}.sh"
    sed -i "s|INITIAL_PROMPT_PLACEHOLDER|$initial_prompt|g" "$SESSIONS_DIR/start_${agent_name}.sh"
    sed -i "s|MAX_TURNS_PLACEHOLDER|$MAX_TURNS|g" "$SESSIONS_DIR/start_${agent_name}.sh"
    sed -i "s|LOG_FILE_PLACEHOLDER|$log_file|g" "$SESSIONS_DIR/start_${agent_name}.sh"
    sed -i "s|SESSION_FILE_PLACEHOLDER|$session_file|g" "$SESSIONS_DIR/start_${agent_name}.sh"
    
    chmod +x "$SESSIONS_DIR/start_${agent_name}.sh"
    
    # Start agent in tmux session
    tmux new-session -d -s "agent-$agent_name" \
        "timeout $AGENT_TIMEOUT $SESSIONS_DIR/start_${agent_name}.sh || echo 'Agent completed or timed out'; read -p 'Press enter to close...'"
    
    print_status "$GREEN" "$agent_name" "Agent started in tmux session: agent-$agent_name"
}

# Function to start all agents
start_all_agents() {
    print_status "$BLUE" "SYSTEM" "Starting all agents..."
    
    # Alpha starts with epic context
    local epic_context=$(cat "$SESSIONS_DIR/epic_context.txt")
    start_agent "alpha" "$PURPLE" "$BASE_REPO_DIR" \
        "Analyze this epic and coordinate the team: $epic_context"
    
    # Wait for Alpha to create initial plan
    print_status "$BLUE" "SYSTEM" "Waiting for Alpha to initialize..."
    sleep 10
    
    # Start builders in parallel (they wait for Alpha's handoff)
    start_agent "beta" "$GREEN" "$BASE_REPO_DIR/../am-agents-core" \
        "Wait for task assignment from Alpha via memory system, then implement core features for epic NMSTX-${EPIC_ID}"
    
    start_agent "delta" "$BLUE" "$BASE_REPO_DIR/../am-agents-api" \
        "Wait for task assignment from Alpha via memory system, then implement API endpoints for epic NMSTX-${EPIC_ID}"
    
    start_agent "epsilon" "$YELLOW" "$BASE_REPO_DIR/../am-agents-tools" \
        "Wait for task assignment from Alpha via memory system, then implement tool integrations for epic NMSTX-${EPIC_ID}"
    
    # Gamma starts immediately to prepare tests
    start_agent "gamma" "$RED" "$BASE_REPO_DIR/../am-agents-tests" \
        "Prepare test structure for epic NMSTX-${EPIC_ID} while waiting for components from other agents. Start immediately with test planning."
}

# Function to show agent status
show_status() {
    print_status "$BLUE" "SYSTEM" "Agent Status:"
    echo "----------------------------------------"
    
    for agent in alpha beta delta epsilon gamma; do
        if tmux has-session -t "agent-$agent" 2>/dev/null; then
            echo -e "${GREEN}✓${NC} $agent: Running"
            
            # Show session file status
            local session_file="$SESSIONS_DIR/${agent}_session.txt"
            if [[ -f "$session_file" ]] && [[ -s "$session_file" ]]; then
                echo "    Session: $(cat "$session_file")"
            else
                echo "    Session: Initializing..."
            fi
        else
            echo -e "${RED}✗${NC} $agent: Not running"
        fi
    done
    
    echo "----------------------------------------"
    echo ""
    echo "Useful commands:"
    echo "  View logs:        tail -f $LOGS_DIR/<agent>_*.log"
    echo "  Attach to agent:  tmux attach -t agent-<n>"
    echo "  Monitor all:      $SCRIPT_DIR/monitor_agents.sh"
    echo "  Continue agent:   $SCRIPT_DIR/run_agent.sh <agent> --continue"
    echo "  Communicate:      $SCRIPT_DIR/agent_communicate.sh <from> <to> 'message'"
    echo ""
    echo "Tips:"
    echo "  - Agents will stop at $MAX_TURNS turns"
    echo "  - Use --continue to resume when they stop"
    echo "  - Check monitor_agents.sh for coordination status"
}

# Function to show usage
show_usage() {
    echo "Usage: $0 <epic_name> <epic_id>"
    echo ""
    echo "Examples:"
    echo "  $0 'MCP Integration' 127"
    echo "  $0 'OAuth2 Implementation' 128"
    echo ""
    echo "Options:"
    echo "  REUSE_BRANCHES=true    Reuse existing branches if found"
    echo "  MAX_TURNS=50          Set maximum turns per agent (default: 30)"
    echo "  AGENT_TIMEOUT=3600    Set agent timeout in seconds (default: 7200)"
    echo ""
    echo "Full example:"
    echo "  REUSE_BRANCHES=true MAX_TURNS=50 $0 'Continue Epic' 127"
}

# Main execution
main() {
    if [[ -z "$EPIC_NAME" ]] || [[ -z "$EPIC_ID" ]]; then
        show_usage
        exit 1
    fi
    
    print_status "$PURPLE" "SYSTEM" "Starting Multi-Agent Team"
    echo "Epic: $EPIC_NAME"
    echo "ID: NMSTX-${EPIC_ID}"
    echo "Max Turns: $MAX_TURNS"
    echo "Timeout: $AGENT_TIMEOUT seconds"
    echo "Branch Mode: $(if [[ "$REUSE_BRANCHES" == "true" ]]; then echo "Reuse existing"; else echo "Create fresh"; fi)"
    echo ""
    
    validate_environment
    setup_worktrees
    create_epic_context
    start_all_agents
    
    # Wait a moment for all agents to initialize
    sleep 5
    
    # Show final status
    show_status
    
    print_status "$GREEN" "SYSTEM" "Team started successfully!"
    print_status "$BLUE" "SYSTEM" "Monitor progress: $SCRIPT_DIR/monitor_agents.sh"
    print_status "$YELLOW" "SYSTEM" "Agents will need --continue after $MAX_TURNS turns"
}

# Handle script termination
trap 'print_status "$YELLOW" "SYSTEM" "Script interrupted. Agents remain running in tmux sessions."; exit 130' INT TERM

# Run main
main "$@"