#!/bin/bash
# agent_communicate_reply.sh - Reply to inter-agent messages

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$SCRIPT_DIR"
COMM_DIR="${BASE_DIR}/communications"

# Arguments
MESSAGE_ID="${1:-}"
SENDER_AGENT="${2:-}"
REPLY_MESSAGE="${3:-}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Validate inputs
if [[ -z "$MESSAGE_ID" ]] || [[ -z "$SENDER_AGENT" ]] || [[ -z "$REPLY_MESSAGE" ]]; then
    echo "Usage: $0 <message_id> <sender_agent> <reply_message>"
    echo ""
    echo "Example:"
    echo "  $0 msg_1234_alpha_to_beta beta \"Task completed successfully\""
    exit 1
fi

# Check if communication directory exists
if [[ ! -d "$COMM_DIR" ]]; then
    echo "❌ Communications directory not found: $COMM_DIR"
    exit 1
fi

# Use the main agent_communicate.sh script to send the reply
COMMUNICATE_SCRIPT="$SCRIPT_DIR/agent_communicate.sh"

if [[ ! -f "$COMMUNICATE_SCRIPT" ]]; then
    echo "❌ Agent communication script not found: $COMMUNICATE_SCRIPT"
    exit 1
fi

# Call the reply function in agent_communicate.sh
exec "$COMMUNICATE_SCRIPT" reply "$MESSAGE_ID" "$SENDER_AGENT" "$REPLY_MESSAGE" 