#!/bin/bash
# run_alpha.sh - Run Alpha orchestrator with WhatsApp notifications

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"
PROMPTS_DIR="${BASE_DIR}/agents-prompts"
LOGS_DIR="${BASE_DIR}/logs"
SESSIONS_DIR="${BASE_DIR}/sessions"
WORK_DIR="/root/workspace/am-agents-labs"

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
NC='\033[0m'

# Function to send WhatsApp message
send_whatsapp() {
    local message="$1"
    curl -s -X POST "$WHATSAPP_URL" \
        -H "Content-Type: application/json" \
        -H "apikey: $WHATSAPP_KEY" \
        -d "{\"number\": \"$WHATSAPP_GROUP\", \"text\": \"$message\"}" > /dev/null
}

# Function to escape JSON
escape_json() {
    echo "$1" | sed 's/\\/\\\\/g; s/"/\\"/g; s/\n/\\n/g; s/\r/\\r/g; s/\t/\\t/g'
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
    START_MSG="🎯 *Alpha Orchestrator Started*\n\n📋 Task: $TASK_MSG\n⏰ Time: $(date)\n💾 Session: Starting new...\n\n_Alpha will coordinate the team to complete this epic._"
else
    START_MSG="🔄 *Alpha Orchestrator Resumed*\n\n💾 Session: $RESUME_SESSION\n⏰ Time: $(date)\n\n_Continuing previous orchestration..._"
fi
send_whatsapp "$START_MSG"

echo -e "${PURPLE}[ALPHA]${NC} Starting orchestrator..."
echo "Task: ${TASK_MSG:-Resuming session}"
echo "Log: $LOG_FILE"

# Run Alpha
cd "$WORK_DIR"

if [[ -n "$RESUME_SESSION" ]]; then
    # Resume existing session
    CLAUDE_OUTPUT=$(claude --continue \
        --max-turns "$MAX_TURNS" \
        --output-format json \
        2>&1 | tee "$LOG_FILE")
else
    # Start new session
    SYSTEM_PROMPT=$(cat "$PROMPTS_DIR/alpha_prompt.md")
    
    # Add orchestration context
    ORCHESTRATION_CONTEXT="
IMPORTANT: You have access to these scripts to manage your team:
- $SCRIPT_DIR/run_beta.sh \"task\" - Start Beta on core development
- $SCRIPT_DIR/run_delta.sh \"task\" - Start Delta on API development  
- $SCRIPT_DIR/run_epsilon.sh \"task\" - Start Epsilon on tool development
- $SCRIPT_DIR/run_gamma.sh \"task\" - Start Gamma on testing

Use send_whatsapp_message frequently to report progress and ask questions to the technical team.
"
    
    CLAUDE_OUTPUT=$(claude -p "$TASK_MSG" \
        --append-system-prompt "$SYSTEM_PROMPT$ORCHESTRATION_CONTEXT" \
        --max-turns "$MAX_TURNS" \
        --output-format json \
        2>&1 | tee "$LOG_FILE")
fi

# Save output
echo "$CLAUDE_OUTPUT" > "$OUTPUT_FILE"

# Extract session ID
SESSION_ID=$(echo "$CLAUDE_OUTPUT" | jq -r '.session_id // empty' | tail -1)
if [[ -n "$SESSION_ID" ]]; then
    echo "$SESSION_ID" > "$SESSION_FILE"
fi

# Extract final result
FINAL_RESULT=$(echo "$CLAUDE_OUTPUT" | jq -r '.result // "No result found"' | tail -1)
TRUNCATED_RESULT=$(echo "$FINAL_RESULT" | head -c 1000)

# Prepare completion message
COMPLETION_MSG="✅ *Alpha Orchestrator Complete*\n\n"
COMPLETION_MSG+="📋 Task: ${TASK_MSG:-Session resumed}\n"
COMPLETION_MSG+="⏰ Duration: Started at $(date)\n"
COMPLETION_MSG+="💾 Session: ${SESSION_ID:-Unknown}\n\n"
COMPLETION_MSG+="📊 *Final Output:*\n"
COMPLETION_MSG+="> ${TRUNCATED_RESULT}...\n\n"
COMPLETION_MSG+="🔄 *To continue this session:*\n"
COMPLETION_MSG+="\`RESUME_SESSION=$SESSION_ID $0\`\n\n"
COMPLETION_MSG+="_Check logs at: ${LOG_FILE}_"

# Send completion notification
send_whatsapp "$COMPLETION_MSG"

echo -e "${GREEN}[ALPHA]${NC} Orchestration complete!"
echo "Session ID: ${SESSION_ID:-Not found}"
echo "To continue: RESUME_SESSION=$SESSION_ID $0"