#!/bin/bash
# agent_communicate.sh - Asynchronous inter-agent communication system

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$SCRIPT_DIR"
SESSIONS_DIR="${BASE_DIR}/sessions"
LOGS_DIR="${BASE_DIR}/logs"
COMM_DIR="${BASE_DIR}/communications"

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

# Ensure communication directories exist
mkdir -p "$SESSIONS_DIR" "$LOGS_DIR" "$COMM_DIR"

# Function to send WhatsApp message
send_whatsapp() {
    local message="$1"
    local json_payload=$(jq -n --arg text "$message" --arg number "$WHATSAPP_GROUP" '{number: $number, text: $text}')
    
    curl -s -X POST "$WHATSAPP_URL" \
        -H "Content-Type: application/json" \
        -H "apikey: $WHATSAPP_KEY" \
        -d "$json_payload" > /dev/null 2>&1
}

# Function to get agent details
get_agent_details() {
    local agent="$1"
    case "$agent" in
        "alpha") echo "🎯 Alpha Orchestrator" ;;
        "beta") echo "🔨 Beta Core Builder" ;;
        "delta") echo "🏗️ Delta API Builder" ;;
        "epsilon") echo "🔧 Epsilon Tool Builder" ;;
        "gamma") echo "🧪 Gamma Quality Engineer" ;;
        *) echo "🤖 Unknown Agent" ;;
    esac
}

# Function to check if agent has active session
check_agent_session() {
    local agent="$1"
    local session_file="$SESSIONS_DIR/${agent}_session.txt"
    local tmux_file="$SESSIONS_DIR/${agent}_tmux.txt"
    
    # Check if agent has both Claude session and tmux session
    if [[ -f "$session_file" ]] && [[ -f "$tmux_file" ]]; then
        local session_id=$(cat "$session_file")
        local tmux_session=$(cat "$tmux_file")
        
        # Verify tmux session is still active
        if tmux has-session -t "$tmux_session" 2>/dev/null; then
            echo "ACTIVE:$session_id:$tmux_session"
            return 0
        fi
    fi
    
    echo "INACTIVE"
    return 1
}

# Function to deliver message to agent's Claude session
deliver_message_to_agent() {
    local target_agent="$1"
    local sender_agent="$2"
    local message="$3"
    local message_id="$4"
    
    # Get agent session info
    local session_info=$(check_agent_session "$target_agent")
    if [[ "$session_info" == "INACTIVE" ]]; then
        return 1
    fi
    
    # Parse session info
    local session_id=$(echo "$session_info" | cut -d: -f2)
    local tmux_session=$(echo "$session_info" | cut -d: -f3)
    
    # Create message file for the target agent
    local msg_file="$COMM_DIR/${target_agent}_incoming_${message_id}.json"
    cat > "$msg_file" << EOF
{
    "message_id": "$message_id",
    "from": "$sender_agent",
    "to": "$target_agent",
    "message": "$message",
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "status": "pending"
}
EOF
    
    # Inject message into the agent's Claude session via tmux
    local claude_message="[INTER-AGENT MESSAGE]
From: $(get_agent_details "$sender_agent")
Message ID: $message_id

$message

Please respond using the agent_communicate_reply tool with message_id: $message_id
After responding, continue with your current task."
    
    # Send the message to the Claude session in tmux
    tmux send-keys -t "$tmux_session" "# MESSAGE FROM $sender_agent: $message" Enter
    
    # Use a more direct approach - continue the Claude session with the message
    cd "$SESSIONS_DIR"
    echo "$claude_message" | claude --continue \
        --session-id "$session_id" \
        --max-turns 1 \
        --output-format json > /dev/null 2>&1 &
    
    # Mark message as delivered
    jq '.status = "delivered"' "$msg_file" > "${msg_file}.tmp" && mv "${msg_file}.tmp" "$msg_file"
    
    return 0
}

# Function to send agent communication
send_agent_message() {
    local sender="$1"
    local target="$2"
    local message="$3"
    
    # Generate unique message ID
    local message_id="msg_$(date +%s)_${sender}_to_${target}"
    local timestamp=$(date)
    
    # Log the communication attempt
    local log_file="$LOGS_DIR/agent_comm_${message_id}.log"
    {
        echo "=== Agent Communication ==="
        echo "Message ID: $message_id"
        echo "Time: $timestamp"
        echo "From: $sender -> $target"
        echo "Message: $message"
        echo "=========================="
    } > "$log_file"
    
    # Send WhatsApp notification
    local whatsapp_msg="💬 *Agent Communication*

👤 **From:** $(get_agent_details "$sender")
👤 **To:** $(get_agent_details "$target")
🆔 **ID:** $message_id
⏰ **Time:** $(date +%H:%M:%S)

📝 **Message:**
> $message

🔄 _Delivering message..._"
    
    send_whatsapp "$whatsapp_msg"
    
    # Check if target agent is active
    local session_info=$(check_agent_session "$target")
    if [[ "$session_info" == "INACTIVE" ]]; then
        # Target agent not active - suggest starting it
        echo "❌ Agent $target is not currently active"
        echo ""
        echo "💡 To start $target agent:"
        echo "   ./agent-scripts/run_${target}.sh \"$message\""
        echo ""
        echo "📊 Communication Status: FAILED - Target agent offline"
        
        # Send failure notification
        local failure_msg="❌ *Message Delivery Failed*

👤 **$sender** → **$target**
🆔 **ID:** $message_id
🚫 **Error:** Target agent not active

💡 **To start target agent:**
\`./agent-scripts/run_${target}.sh \"$message\"\`"
        
        send_whatsapp "$failure_msg"
        return 1
    fi
    
    # Deliver message to target agent
    if deliver_message_to_agent "$target" "$sender" "$message" "$message_id"; then
        echo "✅ Message sent successfully to $target"
        echo ""
        echo "📊 Communication Details:"
        echo "   Message ID: $message_id"
        echo "   From: $(get_agent_details "$sender")"
        echo "   To: $(get_agent_details "$target")"
        echo "   Status: DELIVERED"
        echo ""
        echo "⏳ Please wait for $target to respond..."
        echo "   $target will process your message and may reply using inter-agent communication."
        echo "   You can continue with your current task while waiting."
        echo ""
        echo "📋 Check communication log: $log_file"
        
        # Send success notification
        local success_msg="✅ *Message Delivered*

👤 **$sender** → **$target**
🆔 **ID:** $message_id
📨 **Status:** DELIVERED
🖥️  **Session:** $(echo "$session_info" | cut -d: -f3)

⏳ _Waiting for $target to respond..._"
        
        send_whatsapp "$success_msg"
        return 0
    else
        echo "❌ Failed to deliver message to $target"
        echo ""
        echo "📊 Communication Status: FAILED - Delivery error"
        return 1
    fi
}

# Function to reply to a message
reply_to_message() {
    local message_id="$1"
    local sender="$2"
    local reply_message="$3"
    
    # Find the original message file
    local original_msg_file="$COMM_DIR/${sender}_incoming_${message_id}.json"
    if [[ ! -f "$original_msg_file" ]]; then
        echo "❌ Original message $message_id not found"
        return 1
    fi
    
    # Parse original message
    local original_from=$(jq -r '.from' "$original_msg_file")
    local original_to=$(jq -r '.to' "$original_msg_file")
    
    # Create reply message ID
    local reply_id="reply_$(date +%s)_${sender}_to_${original_from}"
    
    # Send reply back to original sender
    echo "🔄 Sending reply to $original_from..."
    send_agent_message "$sender" "$original_from" "Reply to message $message_id: $reply_message"
    
    # Mark original message as replied
    jq '.status = "replied" | .reply_id = "'$reply_id'"' "$original_msg_file" > "${original_msg_file}.tmp" && mv "${original_msg_file}.tmp" "$original_msg_file"
    
    return 0
}

# Function to check for pending messages for an agent
check_pending_messages() {
    local agent="$1"
    local pending_files=("$COMM_DIR/${agent}_incoming_"msg_*.json)
    
    if [[ -f "${pending_files[0]}" ]]; then
        echo "📨 Pending messages for $agent:"
        for msg_file in "${pending_files[@]}"; do
            if [[ -f "$msg_file" ]]; then
                local msg_id=$(jq -r '.message_id' "$msg_file")
                local from=$(jq -r '.from' "$msg_file")
                local message=$(jq -r '.message' "$msg_file")
                local status=$(jq -r '.status' "$msg_file")
                
                echo "  🆔 ID: $msg_id"
                echo "  👤 From: $(get_agent_details "$from")"
                echo "  📝 Message: $message"
                echo "  📊 Status: $status"
                echo "  ---"
            fi
        done
    else
        echo "📭 No pending messages for $agent"
    fi
}

# Function to list active agents
list_active_agents() {
    echo "🤖 Active Agents:"
    local found_active=false
    
    for agent in alpha beta delta epsilon gamma; do
        local session_info=$(check_agent_session "$agent")
        if [[ "$session_info" != "INACTIVE" ]]; then
            local session_id=$(echo "$session_info" | cut -d: -f2)
            local tmux_session=$(echo "$session_info" | cut -d: -f3)
            echo "  ✅ $(get_agent_details "$agent")"
            echo "     Session: $session_id"
            echo "     TMux: $tmux_session"
            found_active=true
        fi
    done
    
    if [[ "$found_active" == "false" ]]; then
        echo "  ❌ No active agents found"
        echo ""
        echo "💡 Start agents with:"
        echo "   ./agent-scripts/run_<agent>.sh \"<task>\""
    fi
}

# Main command handling
case "${1:-}" in
    "")
        echo "Usage: $0 <sender> <target> <message>"
        echo "   or: $0 reply <message_id> <sender> <reply_message>"
        echo "   or: $0 check <agent>"
        echo "   or: $0 list"
        echo ""
        echo "Examples:"
        echo "  $0 alpha beta \"Please implement user authentication\""
        echo "  $0 reply msg_1234_alpha_to_beta beta \"Authentication is complete\""
        echo "  $0 check beta"
        echo "  $0 list"
        exit 1
        ;;
    "reply")
        if [[ $# -ne 4 ]]; then
            echo "Usage: $0 reply <message_id> <sender> <reply_message>"
            exit 1
        fi
        reply_to_message "$2" "$3" "$4"
        ;;
    "check")
        if [[ -z "${2:-}" ]]; then
            echo "Usage: $0 check <agent>"
            exit 1
        fi
        check_pending_messages "$2"
        ;;
    "list")
        list_active_agents
        ;;
    *)
        if [[ $# -ne 3 ]]; then
            echo "Usage: $0 <sender> <target> <message>"
            exit 1
        fi
        
        # Validate agent names
        for agent in "$1" "$2"; do
            if [[ ! "$agent" =~ ^(alpha|beta|delta|epsilon|gamma)$ ]]; then
                echo "❌ Invalid agent name: $agent"
                echo "Valid agents: alpha, beta, delta, epsilon, gamma"
                exit 1
            fi
        done
        
        send_agent_message "$1" "$2" "$3"
        ;;
esac