#!/bin/bash
# run_alpha.sh - Run Alpha orchestrator with WhatsApp notifications

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

# Setup directories and files early
mkdir -p "$LOGS_DIR" "$SESSIONS_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$LOGS_DIR/${AGENT_NAME}_${TIMESTAMP}.log"
SESSION_FILE="$SESSIONS_DIR/${AGENT_NAME}_session.txt"
OUTPUT_FILE="$SESSIONS_DIR/${AGENT_NAME}_output_${TIMESTAMP}.json"

# Function to send WhatsApp message
send_whatsapp() {
    local message="$1"
    # Create proper JSON payload without over-escaping
    local json_payload=$(jq -n --arg text "$message" --arg number "$WHATSAPP_GROUP" '{number: $number, text: $text}')
    
    echo -e "${BLUE}[WHATSAPP]${NC} Sending: ${message:0:100}..." | tee -a "$LOG_FILE"
    
    local response=$(curl -s -X POST "$WHATSAPP_URL" \
        -H "Content-Type: application/json" \
        -H "apikey: $WHATSAPP_KEY" \
        -d "$json_payload" 2>&1)
    
    local exit_code=$?
    
    if [[ $exit_code -eq 0 ]] && [[ "$response" == *"PENDING"* || "$response" == *"SUCCESS"* ]]; then
        echo -e "${GREEN}[WHATSAPP]${NC} Message sent successfully" | tee -a "$LOG_FILE"
    else
        echo -e "${YELLOW}[WHATSAPP]${NC} Warning: Message may have failed" | tee -a "$LOG_FILE"
        echo -e "${YELLOW}[WHATSAPP]${NC} Response: $response" | tee -a "$LOG_FILE"
        echo -e "${YELLOW}[WHATSAPP]${NC} Exit code: $exit_code" | tee -a "$LOG_FILE"
    fi
}

# Validate input
if [[ -z "$TASK_MSG" ]] && [[ -z "$RESUME_SESSION" ]]; then
    echo "Usage: $0 <task_message>"
    echo "   or: RESUME_SESSION=<session_id> $0"
    exit 1
fi

# Check if claude is available
if ! command -v claude &> /dev/null; then
    echo -e "${RED}Error: claude command not found in PATH${NC}"
    send_whatsapp "❌ Alpha failed: claude CLI not found"
    exit 1
fi

# Test claude with a simple command
echo -e "${PURPLE}[ALPHA]${NC} Testing claude CLI..." | tee -a "$LOG_FILE"
TEST_OUTPUT=$(claude -p "Say 'ready'" --output-format json 2>&1 || true)

# Check if we got a valid JSON response with success
if [[ -z "$TEST_OUTPUT" ]]; then
    echo -e "${RED}Error: Claude CLI produced no output${NC}" | tee -a "$LOG_FILE"
    send_whatsapp "❌ Alpha failed: Claude CLI not responding"
    exit 1
elif echo "$TEST_OUTPUT" | jq -e '.result == "ready"' > /dev/null 2>&1; then
    echo -e "${GREEN}[ALPHA]${NC} Claude CLI test passed" | tee -a "$LOG_FILE"
elif echo "$TEST_OUTPUT" | jq -e '.is_error == true' > /dev/null 2>&1; then
    echo -e "${RED}Error: Claude CLI returned an error${NC}" | tee -a "$LOG_FILE"
    echo "Test output: $TEST_OUTPUT" | tee -a "$LOG_FILE"
    send_whatsapp "❌ Alpha failed: Claude CLI returned error"
    exit 1
else
    # Check for non-JSON error output (command not found, etc.)
    if [[ "$TEST_OUTPUT" == *"command not found"* ]] || [[ "$TEST_OUTPUT" == *"No such file"* ]]; then
        echo -e "${RED}Error: Claude CLI test failed${NC}" | tee -a "$LOG_FILE"
        echo "Test output: $TEST_OUTPUT" | tee -a "$LOG_FILE"
        send_whatsapp "❌ Alpha failed: Claude CLI not responding correctly"
        exit 1
    else
        echo -e "${GREEN}[ALPHA]${NC} Claude CLI test passed (unexpected format but no errors)" | tee -a "$LOG_FILE"
    fi
fi

# Send start notification
if [[ -n "$TASK_MSG" ]]; then
    START_MSG="🎯 *Alpha Orchestrator Started*

📋 Task: $TASK_MSG
⏰ Time: $(date)
💾 Session: Starting new...

_Alpha will coordinate the team to complete this epic._"
else
    START_MSG="🔄 *Alpha Orchestrator Resumed*

💾 Session: $RESUME_SESSION
⏰ Time: $(date)

_Continuing previous orchestration..._"
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

# Check if send_whatsapp_message tool is available
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
    CLAUDE_OUTPUT=$(claude --continue \
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
