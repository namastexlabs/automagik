#!/bin/bash
# run_gamma.sh - Run Gamma (Quality Engineer) with WhatsApp notifications

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"
PROMPTS_DIR="${BASE_DIR}/agents-prompts"
LOGS_DIR="${BASE_DIR}/logs"
SESSIONS_DIR="${BASE_DIR}/sessions"
WORK_DIR="/root/workspace/am-agents-tests"

# Agent configuration
AGENT_NAME="gamma"
TASK_MSG="${1:-}"
MAX_TURNS="${MAX_TURNS:-20}"
RESUME_SESSION="${RESUME_SESSION:-}"

# WhatsApp configuration
WHATSAPP_URL="http://192.168.112.142:8080/message/sendText/SofIA"
WHATSAPP_GROUP="120363404050997890@g.us"
WHATSAPP_KEY="namastex888"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
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
    
    echo -e "${BLUE}[WHATSAPP]${NC} Sending: ${message:0:100}..." | tee -a "$LOG_FILE"
    
    local response=$(curl -s -X POST "$WHATSAPP_URL" \
        -H "Content-Type: application/json" \
        -H "apikey: $WHATSAPP_KEY" \
        -d "$json_payload" 2>&1)
    
    local exit_code=$?
    
    if [[ $exit_code -eq 0 ]] && [[ "$response" == *"PENDING"* || "$response" == *"SUCCESS"* ]]; then
        echo -e "${GREEN}[WHATSAPP]${NC} Message sent successfully" | tee -a "$LOG_FILE"
    else
        echo -e "${RED}[WHATSAPP]${NC} Failed to send message. Response: $response" | tee -a "$LOG_FILE"
    fi
}

# Validate input
if [[ -z "$TASK_MSG" ]] && [[ -z "$RESUME_SESSION" ]]; then
    echo "Usage: $0 <task_message>"
    echo "   or: RESUME_SESSION=<session_id> $0"
    exit 1
fi

# Setup
mkdir -p "$LOGS_DIR" "$SESSIONS_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$LOGS_DIR/${AGENT_NAME}_${TIMESTAMP}.log"
SESSION_FILE="$SESSIONS_DIR/${AGENT_NAME}_session.txt"
OUTPUT_FILE="$SESSIONS_DIR/${AGENT_NAME}_output_${TIMESTAMP}.json"

# Send start notification
if [[ -n "$TASK_MSG" ]]; then
    START_MSG="✅ *Gamma Quality Engineer Started*

📋 Task: $TASK_MSG
📁 Workspace: am-agents-tests
⏰ Time: $(date)
💾 Session: Starting new...

_Gamma will ensure quality through testing._"
else
    START_MSG="🔄 *Gamma Quality Engineer Resumed*

💾 Session: $RESUME_SESSION
📁 Workspace: am-agents-tests
⏰ Time: $(date)

_Continuing quality assurance..._"
fi
send_whatsapp "$START_MSG"

echo -e "${RED}[GAMMA]${NC} Starting quality engineer..."
echo "Task: ${TASK_MSG:-Resuming session}"
echo "Workspace: $WORK_DIR"
echo "Log: $LOG_FILE"

# Run Gamma
echo -e "${GREEN}[GAMMA]${NC} Changing to work directory: $WORK_DIR" | tee -a "$LOG_FILE"
cd "$WORK_DIR"

# Verify we're in the right place
echo -e "${GREEN}[GAMMA]${NC} Current directory: $(pwd)" | tee -a "$LOG_FILE"
echo -e "${GREEN}[GAMMA]${NC} Checking workspace..." | tee -a "$LOG_FILE"

# Check if this workspace has pyproject.toml (should be a valid project)
if [[ ! -f "pyproject.toml" ]]; then
    echo -e "${RED}[GAMMA]${NC} Error: No pyproject.toml found in workspace" | tee -a "$LOG_FILE"
    send_whatsapp "❌ Gamma failed: Invalid workspace at $WORK_DIR"
    exit 1
fi

# Check git status in this workspace
GIT_BRANCH=$(git branch --show-current 2>/dev/null || echo "unknown")
echo -e "${GREEN}[GAMMA]${NC} Git branch: $GIT_BRANCH" | tee -a "$LOG_FILE"

# Try to check MCP tools from this directory
echo -e "${GREEN}[GAMMA]${NC} Checking MCP tools from workspace..." | tee -a "$LOG_FILE"
MCP_CHECK=$(claude mcp list 2>/dev/null | grep "send_whatsapp_message" || echo "")
if [[ -n "$MCP_CHECK" ]]; then
    echo -e "${GREEN}[GAMMA]${NC} WhatsApp MCP tool available: $MCP_CHECK" | tee -a "$LOG_FILE"
else
    echo -e "${YELLOW}[GAMMA]${NC} Warning: send_whatsapp_message MCP tool not found in this workspace" | tee -a "$LOG_FILE"
    echo -e "${YELLOW}[GAMMA]${NC} Claude will run from here anyway for proper context" | tee -a "$LOG_FILE"
fi

if [[ -n "$RESUME_SESSION" ]]; then
    # Resume existing session - run from current workspace
    echo -e "${GREEN}[GAMMA]${NC} Resuming session from workspace..." | tee -a "$LOG_FILE"
    CLAUDE_OUTPUT=$(claude --continue \
        --mcp-config "/root/workspace/.mcp.json" \
        --allowedTools "$(load_allowed_tools)" \
        --max-turns "$MAX_TURNS" \
        --output-format json \
        2>&1 | tee "$LOG_FILE")
else
    # Start new session - run from project root with workspace context
    SYSTEM_PROMPT=$(cat "$PROMPTS_DIR/gamma_prompt.md")
    
    # Add workspace context to the task message
    WORKSPACE_CONTEXT="Working in: $WORK_DIR (am-agents-tests workspace)"
    SAFE_TASK_MSG=$(echo "$TASK_MSG" | tr '\n' ' ' | sed 's/"/\\"/g')
    FULL_TASK_MSG="$WORKSPACE_CONTEXT - $SAFE_TASK_MSG"
    
    # Debug
    echo -e "${GREEN}[GAMMA]${NC} Starting Claude from project root..." | tee -a "$LOG_FILE"
    echo "Task message: $FULL_TASK_MSG" | tee -a "$LOG_FILE"
    echo -e "${GREEN}[GAMMA]${NC} Using system prompt from: $PROMPTS_DIR/gamma_prompt.md" | tee -a "$LOG_FILE"
    
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
    echo -e "${GREEN}[GAMMA]${NC} Session ID saved: $SESSION_ID" | tee -a "$LOG_FILE"
else
    echo -e "${YELLOW}[GAMMA]${NC} Warning: Could not extract session ID from Claude output" | tee -a "$LOG_FILE"
    SESSION_ID="unknown"
fi

# Extract final result from Claude's JSON output
FINAL_RESULT=$(echo "$CLAUDE_OUTPUT" | jq -r '.result // "No result found"' 2>/dev/null | tail -1)
if [[ -z "$FINAL_RESULT" || "$FINAL_RESULT" == "null" ]]; then
    FINAL_RESULT="No result found in Claude output"
fi
TRUNCATED_RESULT=$(echo "$FINAL_RESULT" | head -c 1000)

# Get git status and test results if available
GIT_STATUS=$(cd "$WORK_DIR" && git status --short | head -5 || echo "No changes")
TEST_SUMMARY="Run 'pytest' to see test results"

# Prepare completion message with proper formatting
COMPLETION_MSG="✅ *Gamma Quality Engineer Complete*

📋 Task: ${TASK_MSG:-Session resumed}
📁 Workspace: am-agents-tests
⏰ Duration: Started at $(date)
💾 Session: ${SESSION_ID:-Unknown}

📊 *Git Status:*
\`\`\`
${GIT_STATUS}
\`\`\`

🧪 *Test Summary:*
${TEST_SUMMARY}

📄 *Final Output:*
> ${TRUNCATED_RESULT}...

🔄 *To continue this session:*
\`RESUME_SESSION=$SESSION_ID $0\`

_Check logs at: ${LOG_FILE}_"

# Send completion notification
send_whatsapp "$COMPLETION_MSG"

echo -e "${GREEN}[GAMMA]${NC} Quality assurance complete!"
echo "Session ID: ${SESSION_ID:-Not found}"
echo "To continue: RESUME_SESSION=$SESSION_ID $0"