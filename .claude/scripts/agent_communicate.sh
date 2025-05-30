#!/bin/bash
# agent_communicate.sh - Enable agent-to-agent communication with WhatsApp logging

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SESSIONS_DIR="${SCRIPT_DIR}/../sessions"
LOGS_DIR="${SCRIPT_DIR}/../logs"

# Arguments
FROM_AGENT="${1:-}"
TO_AGENT="${2:-}"
MESSAGE="${3:-}"
MAX_TURNS="${MAX_TURNS:-3}" # Limit interactions

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

# Function to send WhatsApp message
send_whatsapp() {
    local message="$1"
    curl -s -X POST "$WHATSAPP_URL" \
        -H "Content-Type: application/json" \
        -H "apikey: $WHATSAPP_KEY" \
        -d "{\"number\": \"$WHATSAPP_GROUP\", \"text\": \"$message\"}" > /dev/null
}

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

if [[ -z "$FROM_AGENT" ]] || [[ -z "$TO_AGENT" ]] || [[ -z "$MESSAGE" ]]; then
    echo "Usage: $0 <from_agent> <to_agent> <message>"
    echo "Example: $0 alpha beta 'What is the status of core implementation?'"
    echo ""
    echo "Optional: MAX_TURNS=5 $0 alpha beta 'Complex discussion'"
    exit 1
fi

# Validate agent names
for agent in "$FROM_AGENT" "$TO_AGENT"; do
    if [[ ! "$agent" =~ ^(alpha|beta|delta|epsilon|gamma)$ ]]; then
        echo "Error: Invalid agent name: $agent"
        exit 1
    fi
done

# Check if TO agent has a session
TO_SESSION_FILE="$SESSIONS_DIR/${TO_AGENT}_session.txt"
if [[ ! -f "$TO_SESSION_FILE" ]]; then
    echo "Error: No session found for $TO_AGENT"
    echo "Start the agent first with: ./agent-scripts/run_${TO_AGENT}.sh"
    exit 1
fi

# Get session ID
TO_SESSION=$(cat "$TO_SESSION_FILE")

# Format communication message
COMM_MESSAGE="[INTER-AGENT COMMUNICATION]
From: ${FROM_AGENT^^} ($(echo $FROM_AGENT | sed 's/alpha/Orchestrator/;s/beta/Core Builder/;s/delta/API Builder/;s/epsilon/Tool Builder/;s/gamma/Quality Engineer/'))
To: ${TO_AGENT^^}
Message: $MESSAGE

Please respond concisely and return control to your primary task."

# Log the communication
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
COMM_LOG="$LOGS_DIR/communication_${FROM_AGENT}_to_${TO_AGENT}_${TIMESTAMP}.log"

# Send WhatsApp notification about the communication
WHATSAPP_MSG="💬 *Inter-Agent Communication*\n\n"
WHATSAPP_MSG+="From: ${FROM_AGENT^^}\n"
WHATSAPP_MSG+="To: ${TO_AGENT^^}\n"
WHATSAPP_MSG+="Message: $MESSAGE\n"
WHATSAPP_MSG+="\n_Waiting for ${TO_AGENT}'s response..._"

send_whatsapp "$WHATSAPP_MSG"

echo "Sending message from $FROM_AGENT to $TO_AGENT..." | tee "$COMM_LOG"
echo "$COMM_MESSAGE" | tee -a "$COMM_LOG"
echo "---" | tee -a "$COMM_LOG"

# Send message to target agent by continuing their session
cd "$SESSIONS_DIR"  # claude will run from here
RESPONSE=$(claude --continue "$COMM_MESSAGE" \
       --mcp-config "/root/workspace/.mcp.json" \
       --allowedTools "$(load_allowed_tools)" \
       --max-turns "$MAX_TURNS" \
       --output-format json 2>&1 | tee -a "$COMM_LOG")

# Extract the actual response
AGENT_RESPONSE=$(echo "$RESPONSE" | jq -r '.result // .error // "No response"' | tail -1)

echo ""
echo "Response from $TO_AGENT:"
echo "$AGENT_RESPONSE"

# Send response to WhatsApp
RESPONSE_MSG="💬 *Agent Response*\n\n"
RESPONSE_MSG+="${TO_AGENT^^} replied:\n"
RESPONSE_MSG+="> $(echo "$AGENT_RESPONSE" | head -c 500)...\n"
RESPONSE_MSG+="\n_Communication complete_"

send_whatsapp "$RESPONSE_MSG"

echo ""
echo "Communication logged to: $COMM_LOG"
echo ""
echo "Note: If $TO_AGENT needs to continue work, run:"
echo "  RESUME_SESSION=$TO_SESSION ./agent-scripts/run_${TO_AGENT}.sh"