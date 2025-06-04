#!/bin/bash
# update_agents_with_tmux.sh - Add tmux session management to all agent scripts

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENT_SCRIPTS_DIR="$SCRIPT_DIR/agent-scripts"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Function to update an agent script with tmux session management
update_agent_script() {
    local agent_name="$1"
    local agent_file="$AGENT_SCRIPTS_DIR/run_${agent_name}.sh"
    
    if [[ ! -f "$agent_file" ]]; then
        echo -e "${RED}[ERROR]${NC} Agent script not found: $agent_file"
        return 1
    fi
    
    echo -e "${BLUE}[UPDATE]${NC} Updating $agent_name script with tmux session management..."
    
    # Create backup
    cp "$agent_file" "${agent_file}.backup.$(date +%Y%m%d_%H%M%S)"
    
    # Read the current script
    local content=$(cat "$agent_file")
    
    # Check if already updated
    if [[ "$content" == *"TMUX_SESSION_NAME"* ]]; then
        echo -e "${YELLOW}[SKIP]${NC} $agent_name already has tmux session management"
        return 0
    fi
    
    # Create the updated script
    cat > "$agent_file" << 'EOF'
#!/bin/bash
# run_AGENT_NAME.sh - Run AGENT_NAME with WhatsApp notifications and tmux session management

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"
PROMPTS_DIR="${BASE_DIR}/agents-prompts"
LOGS_DIR="${BASE_DIR}/logs"
SESSIONS_DIR="${BASE_DIR}/sessions"

# Find the actual project root (where pyproject.toml exists)
PROJECT_ROOT="/root/workspace/am-agents-labs"
if [[ ! -f "$PROJECT_ROOT/pyproject.toml" ]]; then
    # Try to find project root by looking for pyproject.toml
    CURRENT_DIR="$(pwd)"
    while [[ "$CURRENT_DIR" != "/" ]]; do
        if [[ -f "$CURRENT_DIR/pyproject.toml" ]]; then
            PROJECT_ROOT="$CURRENT_DIR"
            break
        fi
        CURRENT_DIR="$(dirname "$CURRENT_DIR")"
    done
fi

WORK_DIR="/root/workspace/am-agents-WORKSPACE_SUFFIX"

# Agent configuration
AGENT_NAME="AGENT_NAME"
TASK_MSG="${1:-}"
MAX_TURNS="${MAX_TURNS:-20}"
RESUME_SESSION="${RESUME_SESSION:-}"

# TMux session management
TMUX_SESSION_NAME="agent-${AGENT_NAME}"
FORCE_NEW_SESSION="${FORCE_NEW_SESSION:-false}"

# WhatsApp configuration
WHATSAPP_URL="http://192.168.112.142:8080/message/sendText/SofIA"
WHATSAPP_GROUP="120363404050997890@g.us"
WHATSAPP_KEY="namastex888"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
PURPLE='\033[0;35m'
NC='\033[0m'

# Load allowed tools from file
load_allowed_tools() {
    local tools_file="/root/workspace/allowed_tools.json"
    if [[ -f "$tools_file" ]]; then
        # Convert JSON array to comma-separated string
        jq -r '.[]' "$tools_file" | tr '\n' ',' | sed 's/,$//'
    else
        echo "mcp__postgres_automagik_agents__query,mcp__agent-memory__search_memory_nodes,mcp__agent-memory__search_memory_facts,mcp__agent-memory__add_memory"
    fi
}

# Function to send WhatsApp message
send_whatsapp() {
    local message="$1"
    # Create proper JSON payload without over-escaping
    local json_payload=$(jq -n --arg text "$message" --arg number "$WHATSAPP_GROUP" '{number: $number, text: $text}')
    
    echo -e "${BLUE}[WHATSAPP]${NC} Sending: ${message:0:100}..." >&2
    
    local response=$(curl -s -X POST "$WHATSAPP_URL" \
        -H "Content-Type: application/json" \
        -H "apikey: $WHATSAPP_KEY" \
        -d "$json_payload" 2>&1)
    
    local exit_code=$?
    
    if [[ $exit_code -eq 0 ]] && [[ "$response" == *"PENDING"* || "$response" == *"SUCCESS"* ]]; then
        echo -e "${GREEN}[WHATSAPP]${NC} Message sent successfully" >&2
    else
        echo -e "${RED}[WHATSAPP]${NC} Failed to send message. Response: $response" >&2
    fi
}

# Function to check if we're already inside tmux
is_in_tmux() {
    [[ -n "${TMUX:-}" ]]
}

# Function to check if tmux session exists
tmux_session_exists() {
    tmux has-session -t "$TMUX_SESSION_NAME" 2>/dev/null
}

# Function to create or reattach to tmux session
ensure_tmux_session() {
    if is_in_tmux; then
        # Already in tmux, check if it's the correct session
        local current_session=$(tmux display-message -p '#S' 2>/dev/null || echo "")
        if [[ "$current_session" == "$TMUX_SESSION_NAME" ]]; then
            echo -e "${GREEN}[TMUX]${NC} Already in correct tmux session: $TMUX_SESSION_NAME" >&2
            return 0
        else
            echo -e "${YELLOW}[TMUX]${NC} In different tmux session: $current_session, staying here" >&2
            return 0
        fi
    fi
    
    # Not in tmux, need to create or attach to session
    if tmux_session_exists && [[ "$FORCE_NEW_SESSION" != "true" ]]; then
        echo -e "${YELLOW}[TMUX]${NC} Session $TMUX_SESSION_NAME exists, attaching..." >&2
        # Save session info
        echo "$TMUX_SESSION_NAME" > "$SESSIONS_DIR/${AGENT_NAME}_tmux.txt"
        # Re-exec this script inside the existing tmux session
        exec tmux send-keys -t "$TMUX_SESSION_NAME" "cd '$(pwd)' && '$0' '$TASK_MSG'" Enter
    else
        # Kill existing session if force new session
        if [[ "$FORCE_NEW_SESSION" == "true" ]] && tmux_session_exists; then
            echo -e "${YELLOW}[TMUX]${NC} Force new session: killing existing $TMUX_SESSION_NAME" >&2
            tmux kill-session -t "$TMUX_SESSION_NAME"
        fi
        
        # Create new tmux session
        echo -e "${GREEN}[TMUX]${NC} Creating new tmux session: $TMUX_SESSION_NAME" >&2
        echo "$TMUX_SESSION_NAME" > "$SESSIONS_DIR/${AGENT_NAME}_tmux.txt"
        # Re-exec this script inside new tmux session
        exec tmux new-session -d -s "$TMUX_SESSION_NAME" -c "$(pwd)" \; send-keys "'$0' '$TASK_MSG'" Enter \; attach-session
    fi
}

# Validate input
if [[ -z "$TASK_MSG" ]] && [[ -z "$RESUME_SESSION" ]]; then
    echo "Usage: $0 <task_message>"
    echo "   or: RESUME_SESSION=<session_id> $0"
    echo "   or: FORCE_NEW_SESSION=true $0 <task_message>"
    exit 1
fi

# Setup directories
mkdir -p "$LOGS_DIR" "$SESSIONS_DIR"

# Ensure we're running in tmux (this will re-exec if not)
ensure_tmux_session

# If we get here, we're definitely in tmux
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$LOGS_DIR/${AGENT_NAME}_${TIMESTAMP}.log"
SESSION_FILE="$SESSIONS_DIR/${AGENT_NAME}_session.txt"
OUTPUT_FILE="$SESSIONS_DIR/${AGENT_NAME}_output_${TIMESTAMP}.json"

echo -e "${GREEN}[AGENT_NAME_UPPER]${NC} Running in tmux session: $TMUX_SESSION_NAME" | tee -a "$LOG_FILE"

# Send start notification
if [[ -n "$TASK_MSG" ]]; then
    START_MSG="AGENT_EMOJI *AGENT_TITLE Started*

📋 Task: $TASK_MSG
📁 Workspace: WORKSPACE_NAME
⏰ Time: $(date)
🖥️  TMux: $TMUX_SESSION_NAME
💾 Session: Starting new...

_AGENT_DESCRIPTION_"
else
    START_MSG="🔄 *AGENT_TITLE Resumed*

💾 Session: $RESUME_SESSION
📁 Workspace: WORKSPACE_NAME
🖥️  TMux: $TMUX_SESSION_NAME
⏰ Time: $(date)

_Continuing AGENT_ACTION..._"
fi
send_whatsapp "$START_MSG"

echo -e "${GREEN}[AGENT_NAME_UPPER]${NC} Starting AGENT_ACTION..."
echo "Task: ${TASK_MSG:-Resuming session}" | tee -a "$LOG_FILE"
echo "Workspace: $WORK_DIR" | tee -a "$LOG_FILE"
echo "Log: $LOG_FILE" | tee -a "$LOG_FILE"
echo "TMux Session: $TMUX_SESSION_NAME" | tee -a "$LOG_FILE"

# Run Agent
echo -e "${GREEN}[AGENT_NAME_UPPER]${NC} Changing to workspace for context: $WORK_DIR" | tee -a "$LOG_FILE"

# Verify workspace exists and is valid
if [[ ! -d "$WORK_DIR" ]]; then
    echo -e "${RED}[AGENT_NAME_UPPER]${NC} Error: Workspace directory not found: $WORK_DIR" | tee -a "$LOG_FILE"
    send_whatsapp "❌ AGENT_TITLE failed: Workspace not found at $WORK_DIR"
    exit 1
fi

# Check if workspace has pyproject.toml (should be a valid project)
if [[ ! -f "$WORK_DIR/pyproject.toml" ]]; then
    echo -e "${RED}[AGENT_NAME_UPPER]${NC} Error: No pyproject.toml found in workspace" | tee -a "$LOG_FILE"
    send_whatsapp "❌ AGENT_TITLE failed: Invalid workspace at $WORK_DIR"
    exit 1
fi

# Get workspace context but execute Claude from project root for MCP access
echo -e "${GREEN}[AGENT_NAME_UPPER]${NC} Workspace directory: $WORK_DIR" | tee -a "$LOG_FILE"
echo -e "${GREEN}[AGENT_NAME_UPPER]${NC} Executing Claude from project root for MCP access: $PROJECT_ROOT" | tee -a "$LOG_FILE"

# Change to project root for Claude execution (MCP tools need this)
cd "$PROJECT_ROOT"

# Verify we're in the right place and MCP tools are available
echo -e "${GREEN}[AGENT_NAME_UPPER]${NC} Current directory: $(pwd)" | tee -a "$LOG_FILE"
echo -e "${GREEN}[AGENT_NAME_UPPER]${NC} Checking MCP tools..." | tee -a "$LOG_FILE"

# Check if send_whatsapp_message tool is available
MCP_CHECK=$(claude mcp list 2>/dev/null | grep "send_whatsapp_message" || echo "")
if [[ -n "$MCP_CHECK" ]]; then
    echo -e "${GREEN}[AGENT_NAME_UPPER]${NC} WhatsApp MCP tool available: $MCP_CHECK" | tee -a "$LOG_FILE"
else
    echo -e "${YELLOW}[AGENT_NAME_UPPER]${NC} Warning: send_whatsapp_message MCP tool not found" | tee -a "$LOG_FILE"
    echo -e "${YELLOW}[AGENT_NAME_UPPER]${NC} Claude will use script-level notifications only" | tee -a "$LOG_FILE"
fi

if [[ -n "$RESUME_SESSION" ]]; then
    # Resume existing session
    echo -e "${PURPLE}[AGENT_NAME_UPPER]${NC} Resuming session..." | tee -a "$LOG_FILE"
    CLAUDE_OUTPUT=$(claude --continue \
        --mcp-config "/root/workspace/.mcp.json" \
        --allowedTools "$(load_allowed_tools)" \
        --max-turns "$MAX_TURNS" \
        --output-format json \
        2>&1 | tee "$LOG_FILE")
else
    # Start new session - run from project root with workspace context
    SYSTEM_PROMPT=$(cat "$PROMPTS_DIR/AGENT_NAME_prompt.md")
    
    # Add workspace context to the task message
    WORKSPACE_CONTEXT="Working in: $WORK_DIR (WORKSPACE_NAME workspace)"
    SAFE_TASK_MSG=$(echo "$TASK_MSG" | tr '\n' ' ' | sed 's/"/\\"/g')
    FULL_TASK_MSG="$WORKSPACE_CONTEXT - $SAFE_TASK_MSG"
    
    # Debug
    echo -e "${GREEN}[AGENT_NAME_UPPER]${NC} Starting Claude from project root..." | tee -a "$LOG_FILE"
    echo "Task message: $FULL_TASK_MSG" | tee -a "$LOG_FILE"
    echo -e "${GREEN}[AGENT_NAME_UPPER]${NC} Using system prompt from: $PROMPTS_DIR/AGENT_NAME_prompt.md" | tee -a "$LOG_FILE"
    
    CLAUDE_OUTPUT=$(claude -p "$SAFE_TASK_MSG" \
        --append-system-prompt "$SYSTEM_PROMPT" \
        --mcp-config "/root/workspace/.mcp.json" \
        --allowedTools "$(load_allowed_tools)" \
        --max-turns "$MAX_TURNS" \
        --output-format json \
        2>&1 | tee "$LOG_FILE")
fi

# Save output
echo "$CLAUDE_OUTPUT" > "$OUTPUT_FILE"

# Extract session ID from Claude's JSON output (it's all on one line)
SESSION_ID=$(echo "$CLAUDE_OUTPUT" | jq -r '.session_id // empty' 2>/dev/null | grep -v '^$' | tail -1)
if [[ -n "$SESSION_ID" && "$SESSION_ID" != "null" && "$SESSION_ID" != "empty" ]]; then
    echo "$SESSION_ID" > "$SESSION_FILE"
    echo -e "${GREEN}[AGENT_NAME_UPPER]${NC} Session ID saved: $SESSION_ID" | tee -a "$LOG_FILE"
else
    echo -e "${YELLOW}[AGENT_NAME_UPPER]${NC} Warning: Could not extract session ID from Claude output" | tee -a "$LOG_FILE"
    SESSION_ID="unknown"
fi

# Extract final result from Claude's JSON output
FINAL_RESULT=$(echo "$CLAUDE_OUTPUT" | jq -r '.result // "No result found"' 2>/dev/null | tail -1)
if [[ -z "$FINAL_RESULT" || "$FINAL_RESULT" == "null" ]]; then
    FINAL_RESULT="No result found in Claude output"
fi
TRUNCATED_RESULT=$(echo "$FINAL_RESULT" | head -c 1000)

# Get git status for completion message
GIT_STATUS=$(cd "$WORK_DIR" && git status --short | head -5 || echo "No changes")

# Prepare completion message with proper formatting
COMPLETION_MSG="✅ *AGENT_TITLE Complete*

📋 Task: ${TASK_MSG:-Session resumed}
📁 Workspace: WORKSPACE_NAME
⏰ Duration: Started at $(date)
💾 Session: ${SESSION_ID:-Unknown}

📊 *Git Status:*
\`\`\`
${GIT_STATUS}
\`\`\`

📄 *Final Output:*
> ${TRUNCATED_RESULT}...

🔄 *To continue this session:*
\`RESUME_SESSION=$SESSION_ID $0\`

_Check logs at: ${LOG_FILE}_"

# Send completion notification
send_whatsapp "$COMPLETION_MSG"

echo -e "${GREEN}[AGENT_NAME_UPPER]${NC} AGENT_ACTION complete!"
echo "Session ID: ${SESSION_ID:-Not found}"
echo "To continue: RESUME_SESSION=$SESSION_ID $0"
EOF
    
    # Now customize the template for the specific agent
    case "$agent_name" in
        "delta")
            sed -i 's/AGENT_NAME/delta/g' "$agent_file"
            sed -i 's/AGENT_NAME_UPPER/DELTA/g' "$agent_file"
            sed -i 's/WORKSPACE_SUFFIX/api/g' "$agent_file"
            sed -i 's/WORKSPACE_NAME/am-agents-api/g' "$agent_file"
            sed -i 's/AGENT_EMOJI/🏗️/g' "$agent_file"
            sed -i 's/AGENT_TITLE/Delta API Builder/g' "$agent_file"
            sed -i 's/AGENT_DESCRIPTION/Delta will build and maintain APIs./g' "$agent_file"
            sed -i 's/AGENT_ACTION/API development/g' "$agent_file"
            ;;
        "epsilon")
            sed -i 's/AGENT_NAME/epsilon/g' "$agent_file"
            sed -i 's/AGENT_NAME_UPPER/EPSILON/g' "$agent_file"
            sed -i 's/WORKSPACE_SUFFIX/tools/g' "$agent_file"
            sed -i 's/WORKSPACE_NAME/am-agents-tools/g' "$agent_file"
            sed -i 's/AGENT_EMOJI/🔧/g' "$agent_file"
            sed -i 's/AGENT_TITLE/Epsilon Tool Builder/g' "$agent_file"
            sed -i 's/AGENT_DESCRIPTION/Epsilon will create and maintain development tools./g' "$agent_file"
            sed -i 's/AGENT_ACTION/tool development/g' "$agent_file"
            ;;
        "gamma")
            sed -i 's/AGENT_NAME/gamma/g' "$agent_file"
            sed -i 's/AGENT_NAME_UPPER/GAMMA/g' "$agent_file"
            sed -i 's/WORKSPACE_SUFFIX/tests/g' "$agent_file"
            sed -i 's/WORKSPACE_NAME/am-agents-tests/g' "$agent_file"
            sed -i 's/AGENT_EMOJI/🧪/g' "$agent_file"
            sed -i 's/AGENT_TITLE/Gamma Quality Engineer/g' "$agent_file"
            sed -i 's/AGENT_DESCRIPTION/Gamma will ensure quality through testing./g' "$agent_file"
            sed -i 's/AGENT_ACTION/quality assurance/g' "$agent_file"
            ;;
    esac
    
    # Make executable
    chmod +x "$agent_file"
    
    echo -e "${GREEN}[SUCCESS]${NC} Updated $agent_name script with tmux session management"
}

# Main execution
echo -e "${BLUE}[UPDATE]${NC} Adding tmux session management to agent scripts..."

# Update each agent
for agent in delta epsilon gamma; do
    update_agent_script "$agent"
done

echo -e "${GREEN}[COMPLETE]${NC} All agent scripts updated with tmux session management!"
echo ""
echo "Changes made:"
echo "  ✓ Added tmux session management to all agent scripts"
echo "  ✓ Scripts now auto-create tmux sessions when called directly"
echo "  ✓ Enhanced WhatsApp notifications with tmux session info"
echo "  ✓ Session tracking and resumption capabilities"
echo ""
echo "Usage examples:"
echo "  ./agent-scripts/run_delta.sh \"Build user API\""
echo "  ./agent-scripts/run_epsilon.sh \"Create testing tools\""
echo "  ./agent-scripts/run_gamma.sh \"Add quality checks\""
echo "  FORCE_NEW_SESSION=true ./agent-scripts/run_delta.sh \"Fresh start\""
echo ""
echo "All agents will now run in tmux and be visible to monitor_agents.sh!" 