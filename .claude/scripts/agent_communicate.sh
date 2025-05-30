#!/bin/bash
# agent_communicate.sh - Enable agent-to-agent communication

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SESSIONS_DIR="${SCRIPT_DIR}/../sessions"
LOGS_DIR="${SCRIPT_DIR}/../logs"

# Arguments
FROM_AGENT="${1:-}"
TO_AGENT="${2:-}"
MESSAGE="${3:-}"
MAX_TURNS="${MAX_TURNS:-3}" # Limit interactions

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
    echo "Start the agent first with: ./run_agent.sh $TO_AGENT"
    exit 1
fi

# Format communication message
COMM_MESSAGE="[INTER-AGENT COMMUNICATION]
From: $FROM_AGENT
To: $TO_AGENT
Message: $MESSAGE

Please respond concisely and return control to your primary task."

# Log the communication
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
COMM_LOG="$LOGS_DIR/communication_${FROM_AGENT}_to_${TO_AGENT}_${TIMESTAMP}.log"

echo "Sending message from $FROM_AGENT to $TO_AGENT..." | tee "$COMM_LOG"
echo "$COMM_MESSAGE" | tee -a "$COMM_LOG"
echo "---" | tee -a "$COMM_LOG"

# Send message to target agent by continuing their session
cd "$SESSIONS_DIR"  # claude will run from here
claude --continue "$COMM_MESSAGE" \
       --max-turns "$MAX_TURNS" \
       --output-format json 2>&1 | tee -a "$COMM_LOG" | \
       jq -r '.result // .error // "No response"'

echo ""
echo "Communication logged to: $COMM_LOG"