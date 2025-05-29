#!/bin/bash
# run_agent.sh - Run individual agent with specific configuration

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROMPTS_DIR="${SCRIPT_DIR}/agents_prompts"
LOGS_DIR="${SCRIPT_DIR}/logs"
SESSIONS_DIR="${SCRIPT_DIR}/sessions"

# Arguments
AGENT_NAME="${1:-}"
WORK_DIR="${2:-.}"
INITIAL_PROMPT="${3:-}"
MAX_TURNS="${MAX_TURNS:-10}"
RESUME_SESSION="${RESUME_SESSION:-}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

# Validate arguments
if [[ -z "$AGENT_NAME" ]]; then
    echo "Usage: $0 <agent_name> [work_dir] [initial_prompt]"
    echo "Agents: alpha, beta, delta, epsilon, gamma"
    echo ""
    echo "Environment variables:"
    echo "  MAX_TURNS=10        - Maximum conversation turns"
    echo "  RESUME_SESSION=id   - Resume from session ID"
    exit 1
fi

# Validate agent name
if [[ ! "$AGENT_NAME" =~ ^(alpha|beta|delta|epsilon|gamma)$ ]]; then
    echo -e "${RED}Error: Invalid agent name: $AGENT_NAME${NC}"
    exit 1
fi

# Check prompt file
PROMPT_FILE="$PROMPTS_DIR/${AGENT_NAME}.md"
if [[ ! -f "$PROMPT_FILE" ]]; then
    echo -e "${RED}Error: Prompt file not found: $PROMPT_FILE${NC}"
    exit 1
fi

# Setup directories
mkdir -p "$LOGS_DIR" "$SESSIONS_DIR"

# Generate file names
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$LOGS_DIR/${AGENT_NAME}_${TIMESTAMP}.log"
SESSION_FILE="$SESSIONS_DIR/${AGENT_NAME}_session.txt"
OUTPUT_FILE="$SESSIONS_DIR/${AGENT_NAME}_output_${TIMESTAMP}.json"

# Function to run agent
run_agent() {
    cd "$WORK_DIR"
    
    echo -e "${BLUE}Starting $AGENT_NAME agent...${NC}"
    echo "Work directory: $WORK_DIR"
    echo "Log file: $LOG_FILE"
    echo "Session file: $SESSION_FILE"
    
    # Read system prompt
    SYSTEM_PROMPT=$(cat "$PROMPT_FILE")
    
    # Build claude command
    local claude_cmd="claude"
    
    # Add initial prompt if provided
    if [[ -n "$INITIAL_PROMPT" ]]; then
        claude_cmd="$claude_cmd -p \"$INITIAL_PROMPT\""
    fi
    
    # Add resume session if provided
    if [[ -n "$RESUME_SESSION" ]]; then
        claude_cmd="$claude_cmd --resume \"$RESUME_SESSION\""
    fi
    
    # Add system prompt and other options
    claude_cmd="$claude_cmd --append-system-prompt \"\$SYSTEM_PROMPT\""
    claude_cmd="$claude_cmd --max-turns $MAX_TURNS"
    claude_cmd="$claude_cmd --output-format json"
    
    # Execute and capture output
    eval "$claude_cmd" 2>&1 | tee "$LOG_FILE" > "$OUTPUT_FILE"
    
    # Extract session ID
    if [[ -f "$OUTPUT_FILE" ]]; then
        jq -r '.session_id // empty' "$OUTPUT_FILE" > "$SESSION_FILE"
        
        if [[ -s "$SESSION_FILE" ]]; then
            echo -e "${GREEN}Session ID saved: $(cat $SESSION_FILE)${NC}"
        fi
    fi
    
    echo -e "${GREEN}Agent $AGENT_NAME completed${NC}"
}

# Function to continue session
continue_session() {
    if [[ ! -f "$SESSION_FILE" ]]; then
        echo -e "${RED}No session file found for $AGENT_NAME${NC}"
        exit 1
    fi
    
    local session_id=$(cat "$SESSION_FILE")
    if [[ -z "$session_id" ]]; then
        echo -e "${RED}No session ID found${NC}"
        exit 1
    fi
    
    echo -e "${BLUE}Continuing session: $session_id${NC}"
    RESUME_SESSION="$session_id"
}

# Check if continuing previous session
if [[ "$INITIAL_PROMPT" == "--continue" ]]; then
    continue_session
    INITIAL_PROMPT=""
fi

# Run the agent
run_agent

# Show next steps
echo ""
echo "Next steps:"
echo "- View output: jq . $OUTPUT_FILE"
echo "- Continue session: RESUME_SESSION=\$(cat $SESSION_FILE) $0 $AGENT_NAME"
echo "- View logs: tail -f $LOG_FILE"