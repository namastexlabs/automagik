#!/bin/bash
# run_beta.sh - Run Beta (Core Builder) with WhatsApp notifications

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"
PROMPTS_DIR="${BASE_DIR}/agents-prompts"
LOGS_DIR="${BASE_DIR}/logs"
SESSIONS_DIR="${BASE_DIR}/sessions"
WORK_DIR="/root/workspace/am-agents-core"

# Agent configuration
AGENT_NAME="beta"
TASK_MSG="${1:-}"
MAX_TURNS="${MAX_TURNS:-30}"
RESUME_SESSION="${RESUME_SESSION:-}"

# WhatsApp configuration
WHATSAPP_URL="http://192.168.112.142:8080/message/sendText/SofIA"
WHATSAPP_GROUP="120363404050997890@g.us"
WHATSAPP_KEY="namastex888"

# Colors
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
    START_MSG="🔨 *Beta Core Builder Started*\n\n📋 Task: $TASK_MSG\n📁 Workspace: am-agents-core\n⏰ Time: $(date)\n💾 Session: Starting new...\n\n_Beta will implement core features._"
else
    START_MSG="🔄 *Beta Core Builder Resumed*\n\n💾 Session: $RESUME_SESSION\n📁 Workspace: am-agents-core\n⏰ Time: $(date)\n\n_Continuing core implementation..._"
fi
send_whatsapp "$START_MSG"

echo -e "${GREEN}[BETA]${NC} Starting core builder..."
echo "Task: ${TASK_MSG:-Resuming session}"
echo "Workspace: $WORK_DIR"
echo "Log: $LOG_FILE"

# Ensure workspace exists
if [[ ! -d "$WORK_DIR" ]]; then
    echo -e "${YELLOW}[BETA]${NC} Workspace not found. Please run setup_worktrees.sh first."
    send_whatsapp "❌ Beta failed: Workspace not found at $WORK_DIR"
    exit 1
fi

# Run Beta
cd "$WORK_DIR"

if [[ -n "$RESUME_SESSION" ]]; then
    # Resume existing session
    CLAUDE_OUTPUT=$(claude --continue \
        --max-turns "$MAX_TURNS" \
        --output-format json \
        2>&1 | tee "$LOG_FILE")
else
    # Start new session
    SYSTEM_PROMPT=$(cat "$PROMPTS_DIR/beta_prompt.md")
    
    CLAUDE_OUTPUT=$(claude -p "$TASK_MSG" \
        --append-system-prompt "$SYSTEM_PROMPT" \
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

# Get git status for completion message
GIT_STATUS=$(cd "$WORK_DIR" && git status --short | head -5 || echo "No changes")

# Prepare completion message
COMPLETION_MSG="✅ *Beta Core Builder Complete*\n\n"
COMPLETION_MSG+="📋 Task: ${TASK_MSG:-Session resumed}\n"
COMPLETION_MSG+="📁 Workspace: am-agents-core\n"
COMPLETION_MSG+="⏰ Duration: Started at $(date)\n"
COMPLETION_MSG+="💾 Session: ${SESSION_ID:-Unknown}\n\n"
COMPLETION_MSG+="📊 *Git Status:*\n\`\`\`\n${GIT_STATUS}\n\`\`\`\n\n"
COMPLETION_MSG+="📄 *Final Output:*\n"
COMPLETION_MSG+="> ${TRUNCATED_RESULT}...\n\n"
COMPLETION_MSG+="🔄 *To continue this session:*\n"
COMPLETION_MSG+="\`RESUME_SESSION=$SESSION_ID $0\`\n\n"
COMPLETION_MSG+="_Check logs at: ${LOG_FILE}_"

# Send completion notification
send_whatsapp "$COMPLETION_MSG"

echo -e "${GREEN}[BETA]${NC} Core development complete!"
echo "Session ID: ${SESSION_ID:-Not found}"
echo "To continue: RESUME_SESSION=$SESSION_ID $0"