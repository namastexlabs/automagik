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

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROMPTS_DIR="${SCRIPT_DIR}/../agents-prompts"
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
    
    # Check if required commands are available
    for cmd in claude tmux jq git; do
        if ! command -v $cmd &> /dev/null; then
            print_status "$RED" "ERROR" "$cmd not found in PATH"
            exit 1
        fi
    done
    
    print_status "$GREEN" "SYSTEM" "Environment validation complete"
}

# Function to setup worktrees
setup_worktrees() {
    print_status "$BLUE" "SYSTEM" "Setting up worktrees for parallel development..."
    
    cd "$BASE_REPO_DIR"
    
    # Fetch latest
    print_status "$BLUE" "SYSTEM" "Fetching latest from origin..."
    git fetch origin --prune
    
    # Setup worktrees for each agent
    local worktrees=(
        "core:/root/workspace/am-agents-core"
        "api:/root/workspace/am-agents-api"
        "tools:/root/workspace/am-agents-tools"
        "tests:/root/workspace/am-agents-tests"
    )
    
    for worktree_info in "${worktrees[@]}"; do
        IFS=':' read -r component path <<< "$worktree_info"
        local branch_name="NMSTX-${EPIC_ID}-${component}"
        
        print_status "$BLUE" "SETUP" "Creating workspace for $component development..."
        
        # Remove existing worktree if present
        if [[ -d "$path" ]]; then
            print_status "$YELLOW" "SETUP" "Removing existing worktree at $path"
            git worktree remove "$path" --force 2>/dev/null || true
        fi
        
        # Handle existing branches
        if git show-ref --verify --quiet "refs/heads/$branch_name"; then
            if [[ "$REUSE_BRANCHES" == "true" ]]; then
                print_status "$BLUE" "SETUP" "Reusing existing branch $branch_name"
                git worktree add "$path" "$branch_name"
            else
                print_status "$YELLOW" "SETUP" "Removing existing branch $branch_name"
                git branch -D "$branch_name" 2>/dev/null || true
                git worktree add "$path" -b "$branch_name"
            fi
        else
            print_status "$GREEN" "SETUP" "Creating new branch $branch_name"
            git worktree add "$path" -b "$branch_name"
        fi
    done
    
    print_status "$GREEN" "SYSTEM" "Worktrees ready for parallel development!"
}

# Function to create orchestration instructions
create_orchestration_instructions() {
    cat > "$SESSIONS_DIR/orchestration_guide.txt" << 'EOF'
ORCHESTRATION GUIDE FOR ALPHA

You are the orchestrator. The team members are NOT running yet - you will start them as needed.

## Your Tools
- Script location: /root/workspace/am-agents-labs/.claude/scripts/
- Start an agent: ./run_agent.sh <agent> <workspace> "instructions"
- Check status: ./monitor_agents.sh
- Communicate: ./agent_communicate.sh alpha <agent> "message"

## Team Workspaces
- Beta (Core): /root/workspace/am-agents-core
- Delta (API): /root/workspace/am-agents-api  
- Epsilon (Tools): /root/workspace/am-agents-tools
- Gamma (Tests): /root/workspace/am-agents-tests

## How to Start Agents
When you need Beta to work on core features:
```bash
cd /root/workspace/am-agents-labs/.claude/scripts
./run_agent.sh beta /root/workspace/am-agents-core "Implement the user authentication module"
```

## How to Check Progress
```bash
cd /root/workspace/am-agents-labs/.claude/scripts
./monitor_agents.sh
```

## How to Continue Agents
When an agent hits max turns:
```bash
cd /root/workspace/am-agents-labs/.claude/scripts
./run_agent.sh beta --continue
```

## Workflow
1. Analyze the epic and break it down
2. Start agents with specific tasks
3. Monitor their progress
4. Use agent_communicate.sh to coordinate
5. Continue agents when they hit turn limits
6. Merge work when complete

Remember: You control when and how agents start. This gives you full visibility and control.
EOF
}

# Function to create epic context
create_epic_context() {
    cat > "$SESSIONS_DIR/epic_context.txt" << EOF
Epic: $EPIC_NAME
Linear ID: NMSTX-${EPIC_ID}
Start Time: $(date)
Mode: Orchestrator-controlled execution

Your Role: You are Alpha, the orchestrator. You will:
1. Analyze this epic
2. Break it into tasks
3. Start other agents as needed using the provided scripts
4. Monitor and coordinate their work
5. Ensure delivery within 24 hours

The other agents (Beta, Delta, Epsilon, Gamma) are NOT running yet.
You will start them individually with specific tasks.

See orchestration_guide.txt for detailed instructions.
EOF
}

# Function to start alpha orchestrator
start_alpha_orchestrator() {
    print_status "$PURPLE" "ALPHA" "Starting orchestrator..."
    
    local prompt_file="$PROMPTS_DIR/alpha_prompt.md"
    local log_file="$LOGS_DIR/alpha_$(date +%Y%m%d_%H%M%S).log"
    local session_file="$SESSIONS_DIR/alpha_session.txt"
    
    # Kill existing session if present
    if tmux has-session -t "agent-alpha" 2>/dev/null; then
        print_status "$YELLOW" "ALPHA" "Killing existing session..."
        tmux kill-session -t "agent-alpha"
        sleep 2
    fi
    
    # Read the context files
    local epic_context=$(cat "$SESSIONS_DIR/epic_context.txt")
    local orchestration_guide=$(cat "$SESSIONS_DIR/orchestration_guide.txt")
    
    # Create startup script
    cat > "$SESSIONS_DIR/start_alpha.sh" << EOF
#!/bin/bash
cd "$BASE_REPO_DIR"
export AGENT_NAME="alpha"
export EPIC_NAME="$EPIC_NAME"
export EPIC_ID="$EPIC_ID"
export SCRIPT_DIR="$SCRIPT_DIR"

# Read system prompt
SYSTEM_PROMPT=\$(cat "$prompt_file")

# Add orchestration context to system prompt
ENHANCED_PROMPT="\$SYSTEM_PROMPT

IMPORTANT ORCHESTRATION CONTEXT:
$orchestration_guide"

# Start Claude with combined prompt
claude -p "$epic_context" \\
       --append-system-prompt "\$ENHANCED_PROMPT" \\
       --max-turns $MAX_TURNS \\
       --output-format json \\
       2>&1 | tee "$log_file" | \\
       jq -r '.session_id // empty' > "$session_file" || true

# Keep session open
echo ""
echo "Alpha session completed. Max turns: $MAX_TURNS"
echo "To continue: $SCRIPT_DIR/run_agent.sh alpha --continue"
read -p "Press enter to close..."
EOF
    
    chmod +x "$SESSIONS_DIR/start_alpha.sh"
    
    # Start in tmux
    tmux new-session -d -s "agent-alpha" "$SESSIONS_DIR/start_alpha.sh"
    
    print_status "$GREEN" "ALPHA" "Orchestrator started in tmux session: agent-alpha"
}

# Function to show status
show_status() {
    echo ""
    print_status "$BLUE" "SYSTEM" "=== ORCHESTRATION STATUS ==="
    echo ""
    echo "Epic: $EPIC_NAME (NMSTX-${EPIC_ID})"
    echo "Mode: Orchestrator-Controlled Execution"
    echo ""
    echo "Alpha Status:"
    if tmux has-session -t "agent-alpha" 2>/dev/null; then
        echo -e "  ${GREEN}✓${NC} Running as orchestrator"
    else
        echo -e "  ${RED}✗${NC} Not running"
    fi
    echo ""
    echo "Workspaces Created:"
    echo "  • Core:  /root/workspace/am-agents-core  (Beta's workspace)"
    echo "  • API:   /root/workspace/am-agents-api   (Delta's workspace)"
    echo "  • Tools: /root/workspace/am-agents-tools (Epsilon's workspace)"
    echo "  • Tests: /root/workspace/am-agents-tests (Gamma's workspace)"
    echo ""
    echo "Available Commands:"
    echo "  • Watch Alpha:    tmux attach -t agent-alpha"
    echo "  • Monitor all:    $SCRIPT_DIR/monitor_agents.sh"
    echo "  • Continue Alpha: $SCRIPT_DIR/run_agent.sh alpha --continue"
    echo ""
    echo "Alpha will start other agents as needed using:"
    echo "  $SCRIPT_DIR/run_agent.sh <agent> <workspace> \"task\""
    echo ""
    print_status "$GREEN" "SYSTEM" "=== READY FOR ORCHESTRATION ==="
}

# Function to show usage
show_usage() {
    echo "Usage: $0 <epic_name> <epic_id>"
    echo ""
    echo "This script starts ONLY the Alpha orchestrator."
    echo "Alpha will then start other agents as needed."
    echo ""
    echo "Examples:"
    echo "  $0 'User Authentication' 127"
    echo "  $0 'API Rate Limiting' 128"
    echo ""
    echo "Options:"
    echo "  REUSE_BRANCHES=true  - Reuse existing branches"
    echo "  MAX_TURNS=50        - Set orchestrator max turns"
    echo ""
    echo "Example with options:"
    echo "  REUSE_BRANCHES=true $0 'Continue Epic' 127"
}

# Main execution
main() {
    if [[ -z "$EPIC_NAME" ]] || [[ -z "$EPIC_ID" ]]; then
        show_usage
        exit 1
    fi
    
    print_status "$PURPLE" "SYSTEM" "=== ORCHESTRATOR MODE ==="
    echo ""
    echo "Epic: $EPIC_NAME"
    echo "ID: NMSTX-${EPIC_ID}"
    echo "Strategy: Alpha orchestrates, others start on demand"
    echo ""
    
    validate_environment
    setup_worktrees
    create_orchestration_instructions
    create_epic_context
    start_alpha_orchestrator
    
    sleep 3
    show_status
}

# Handle interrupts
trap 'print_status "$YELLOW" "SYSTEM" "Interrupted. Alpha remains in tmux."; exit 130' INT TERM

# Run main
main "$@"