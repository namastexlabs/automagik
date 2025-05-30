#!/bin/bash
# run_alpha.sh - Run Alpha orchestrator with WhatsApp notifications and tmux session management

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

WORK_DIR="$PROJECT_ROOT"

# Agent configuration
AGENT_NAME="alpha"
TASK_MSG="${1:-}"
MAX_TURNS="${MAX_TURNS:-30}"
RESUME_SESSION="${RESUME_SESSION:-}"

# TMux session management
TMUX_SESSION_NAME="agent-${AGENT_NAME}"
FORCE_NEW_SESSION="${FORCE_NEW_SESSION:-false}"

# WhatsApp configuration
WHATSAPP_URL="http://192.168.112.142:8080/message/sendText/SofIA"
WHATSAPP_GROUP="120363404050997890@g.us"
WHATSAPP_KEY="namastex888"

# Colors
PURPLE='\033[0;35m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'
BLUE='\033[0;34m'

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
        echo -e "${YELLOW}[WHATSAPP]${NC} Warning: Message may have failed" >&2
        echo -e "${YELLOW}[WHATSAPP]${NC} Response: $response" >&2
        echo -e "${YELLOW}[WHATSAPP]${NC} Exit code: $exit_code" >&2
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

# Function to create or reattach to tmux session - SIMPLIFIED VERSION
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
        
        # Create a proper command with all environment variables
        local tmux_cmd="cd '$WORK_DIR'"
        [[ -n "$RESUME_SESSION" ]] && tmux_cmd="$tmux_cmd && export RESUME_SESSION='$RESUME_SESSION'"
        [[ -n "$MAX_TURNS" ]] && tmux_cmd="$tmux_cmd && export MAX_TURNS='$MAX_TURNS'"
        [[ -n "$FORCE_NEW_SESSION" ]] && tmux_cmd="$tmux_cmd && export FORCE_NEW_SESSION='$FORCE_NEW_SESSION'"
        tmux_cmd="$tmux_cmd && '$0'"
        [[ -n "$TASK_MSG" ]] && tmux_cmd="$tmux_cmd '$TASK_MSG'"
        
        # Send the command to tmux session
        exec tmux send-keys -t "$TMUX_SESSION_NAME" "$tmux_cmd" Enter
    else
        # Kill existing session if force new session
        if [[ "$FORCE_NEW_SESSION" == "true" ]] && tmux_session_exists; then
            echo -e "${YELLOW}[TMUX]${NC} Force new session: killing existing $TMUX_SESSION_NAME" >&2
            tmux kill-session -t "$TMUX_SESSION_NAME"
        fi
        
        # Create new tmux session
        echo -e "${GREEN}[TMUX]${NC} Creating new tmux session: $TMUX_SESSION_NAME" >&2
        echo "$TMUX_SESSION_NAME" > "$SESSIONS_DIR/${AGENT_NAME}_tmux.txt"
        
        # Create a proper command with all environment variables
        local tmux_cmd="cd '$WORK_DIR'"
        [[ -n "$RESUME_SESSION" ]] && tmux_cmd="$tmux_cmd && export RESUME_SESSION='$RESUME_SESSION'"
        [[ -n "$MAX_TURNS" ]] && tmux_cmd="$tmux_cmd && export MAX_TURNS='$MAX_TURNS'"
        [[ -n "$FORCE_NEW_SESSION" ]] && tmux_cmd="$tmux_cmd && export FORCE_NEW_SESSION='$FORCE_NEW_SESSION'"
        tmux_cmd="$tmux_cmd && '$0'"
        [[ -n "$TASK_MSG" ]] && tmux_cmd="$tmux_cmd '$TASK_MSG'"
        
        # Create new session and attach
        exec tmux new-session -d -s "$TMUX_SESSION_NAME" -c "$WORK_DIR" \; send-keys "$tmux_cmd" Enter \; attach-session
    fi
}

# Validate input
if [[ -z "$TASK_MSG" ]] && [[ -z "$RESUME_SESSION" ]]; then
    echo "Usage: $0 <task_message>"
    echo "   or: RESUME_SESSION=<session_id> $0"
    echo "   or: FORCE_NEW_SESSION=true $0 <task_message>"
    exit 1
fi

# Setup directories and files early
mkdir -p "$LOGS_DIR" "$SESSIONS_DIR"

# Ensure we're running in tmux (this will re-exec if not)
ensure_tmux_session

# If we get here, we're definitely in tmux
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$LOGS_DIR/${AGENT_NAME}_${TIMESTAMP}.log"
SESSION_FILE="$SESSIONS_DIR/${AGENT_NAME}_session.txt"
OUTPUT_FILE="$SESSIONS_DIR/${AGENT_NAME}_output_${TIMESTAMP}.json"

echo -e "${PURPLE}[ALPHA]${NC} Running in tmux session: $TMUX_SESSION_NAME" | tee -a "$LOG_FILE"

# Send start notification
if [[ -n "$RESUME_SESSION" ]]; then
    START_MSG="🔄 *Alpha Orchestrator Resumed*

💾 Session: $RESUME_SESSION
⏰ Time: $(date)

_Continuing previous orchestration..._"
else
    START_MSG="🎯 *Alpha Orchestrator Started*

📋 Task: $TASK_MSG
⏰ Time: $(date)
💾 Session: Starting new...

_Alpha will coordinate the team to complete this epic._"
fi
send_whatsapp "$START_MSG"

echo -e "${PURPLE}[ALPHA]${NC} Starting orchestrator..."
echo "Work directory: $WORK_DIR"
echo "Log: $LOG_FILE"

# Run Alpha
echo -e "${PURPLE}[ALPHA]${NC} Changing to work directory: $WORK_DIR" | tee -a "$LOG_FILE"
cd "$WORK_DIR"

# Verify we're in the right place and MCP tools are available
echo -e "${PURPLE}[ALPHA]${NC} Current directory: $(pwd)" | tee -a "$LOG_FILE"
echo -e "${PURPLE}[ALPHA]${NC} Checking MCP tools..." | tee -a "$LOG_FILE"

# Check if send_whatsapp_message tool is available (lightweight check)
MCP_CHECK=$(claude mcp list 2>/dev/null | grep "send_whatsapp_message" || echo "")
if [[ -n "$MCP_CHECK" ]]; then
    echo -e "${GREEN}[ALPHA]${NC} WhatsApp MCP tool available: $MCP_CHECK" | tee -a "$LOG_FILE"
else
    echo -e "${YELLOW}[ALPHA]${NC} Warning: send_whatsapp_message MCP tool not found" | tee -a "$LOG_FILE"
    echo -e "${YELLOW}[ALPHA]${NC} Claude will use script-level notifications only" | tee -a "$LOG_FILE"
fi

if [[ -n "$RESUME_SESSION" ]]; then
    # Resume existing session
    echo -e "${PURPLE}[ALPHA]${NC} Resuming session..." | tee -a "$LOG_FILE"
    
    # Create continuation message
    CONTINUATION_MSG="Continue with the task: ${TASK_MSG:-Continue previous orchestration work}"
    SAFE_CONTINUATION_MSG=$(echo "$CONTINUATION_MSG" | tr '\n' ' ' | sed 's/"/\\"/g')
    
    CLAUDE_OUTPUT=$(claude --resume "$RESUME_SESSION" \
        -p "$SAFE_CONTINUATION_MSG" \
        --mcp-config "/root/workspace/.mcp.json" \
        --allowedTools "$(load_allowed_tools)" \
        --max-turns "$MAX_TURNS" \
        --output-format json \
        2>&1 | tee "$LOG_FILE")
else
    # Start new session
    SYSTEM_PROMPT=$(cat "$PROMPTS_DIR/alpha_prompt.md")
    
    # Simplify task message to avoid command issues
    SAFE_TASK_MSG=$(echo "$TASK_MSG" | tr '\n' ' ' | sed 's/"/\\"/g')
    
    # Debug: Show that we're about to start
    echo -e "${PURPLE}[ALPHA]${NC} Executing Claude..." | tee -a "$LOG_FILE"
    echo "Task message: $SAFE_TASK_MSG" | tee -a "$LOG_FILE"
    echo -e "${PURPLE}[ALPHA]${NC} Using system prompt from: $PROMPTS_DIR/alpha_prompt.md" | tee -a "$LOG_FILE"
    
    # Execute claude and capture output
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

# Check if Claude actually produced output
if [[ -z "$CLAUDE_OUTPUT" ]] || [[ ! -s "$OUTPUT_FILE" ]]; then
    echo -e "${RED}[ALPHA]${NC} Error: Claude did not produce any output" | tee -a "$LOG_FILE"
    echo "Check if claude CLI is working: claude -p 'test'" | tee -a "$LOG_FILE"
    send_whatsapp "❌ Alpha failed to get response from Claude. Check logs at: $LOG_FILE"
    exit 1
fi

# Extract session ID from Claude's JSON output (it's all on one line)
SESSION_ID=$(echo "$CLAUDE_OUTPUT" | jq -r '.session_id // empty' 2>/dev/null | grep -v '^$' | tail -1)
if [[ -n "$SESSION_ID" && "$SESSION_ID" != "null" && "$SESSION_ID" != "empty" ]]; then
    echo "$SESSION_ID" > "$SESSION_FILE"
    echo -e "${GREEN}[ALPHA]${NC} Session ID saved: $SESSION_ID" | tee -a "$LOG_FILE"
else
    echo -e "${YELLOW}[ALPHA]${NC} Warning: Could not extract session ID from Claude output" | tee -a "$LOG_FILE"
    SESSION_ID="unknown"
fi

# Extract final result from Claude's JSON output
FINAL_RESULT=$(echo "$CLAUDE_OUTPUT" | jq -r '.result // "No result found"' 2>/dev/null | tail -1)
if [[ -z "$FINAL_RESULT" || "$FINAL_RESULT" == "null" ]]; then
    FINAL_RESULT="No result found in Claude output"
fi
TRUNCATED_RESULT=$(echo "$FINAL_RESULT" | head -c 1000)

# Prepare completion message with proper formatting
COMPLETION_MSG="✅ *Alpha Orchestrator Complete*

📋 Task: ${TASK_MSG:-Session resumed}
⏰ Duration: Started at $(date)
💾 Session: ${SESSION_ID:-Unknown}

📊 *Final Output:*
> ${TRUNCATED_RESULT}...

🔄 *To continue this session:*
\`RESUME_SESSION=$SESSION_ID $0\`

_Check logs at: ${LOG_FILE}_"

# Send completion notification
send_whatsapp "$COMPLETION_MSG"

echo -e "${GREEN}[ALPHA]${NC} Orchestration complete!"
echo "Session ID: ${SESSION_ID:-Not found}"
echo "To continue: RESUME_SESSION=$SESSION_ID $0"
