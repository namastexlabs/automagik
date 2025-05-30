#!/bin/bash
# run_agent.sh - Run individual agent with specific configuration

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROMPTS_DIR="${SCRIPT_DIR}/../agents_prompts"
LOGS_DIR="${SCRIPT_DIR}/../logs"
SESSIONS_DIR="${SCRIPT_DIR}/../sessions"

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
    echo "To resume without message: $0 <agent_name> --continue"
    echo "To resume with message: $0 <agent_name> . 'new prompt'"
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

# Handle --continue flag
if [[ "$WORK_DIR" == "--continue" ]]; then
    # Just resume, no work dir change
    if [[ ! -f "$SESSION_FILE" ]]; then
        echo -e "${RED}No session file found for $AGENT_NAME${NC}"
        exit 1
    fi
    
    RESUME_SESSION=$(cat "$SESSION_FILE")
    WORK_DIR="."  # Stay in current directory
    INITIAL_PROMPT=""  # No new prompt
fi

# Function to run agent
run_agent() {
    if [[ "$WORK_DIR" != "." ]]; then
        cd "$WORK_DIR"
    fi
    
    echo -e "${BLUE}Starting $AGENT_NAME agent...${NC}"
    echo "Work directory: $(pwd)"
    echo "Log file: $LOG_FILE"
    echo "Session file: $SESSION_FILE"
    
    # Read system prompt
    SYSTEM_PROMPT=$(cat "$PROMPT_FILE")
    
    # Build claude command
    local claude_cmd="claude"
    
    # Handle resume vs new session
    if [[ -n "$RESUME_SESSION" ]]; then
        # Resuming existing session
        if [[ -n "$INITIAL_PROMPT" ]]; then
            # Resume with new prompt
            claude_cmd="$claude_cmd --continue \"$INITIAL_PROMPT\""
        else
            # Just continue without prompt
            claude_cmd="$claude_cmd --continue"
        fi
    else
        # New session
        if [[ -n "$INITIAL_PROMPT" ]]; then
            claude_cmd="$claude_cmd -p \"$INITIAL_PROMPT\""
        fi
    fi
    
    # Add system prompt and other options
    claude_cmd="$claude_cmd --append-system-prompt \"\$SYSTEM_PROMPT\""
    claude_cmd="$claude_cmd --max-turns $MAX_TURNS"
    claude_cmd="$claude_cmd --output-format json"
    
    # Execute and capture output
    eval "$claude_cmd" 2>&1 | tee "$LOG_FILE" > "$OUTPUT_FILE"
    
    # Extract session ID
    if [[ -f "$OUTPUT_FILE" ]]; then
        jq -r '.session_id // empty' "$OUTPUT_FILE" > "$SESSION_FILE.tmp"
        
        if [[ -s "$SESSION_FILE.tmp" ]]; then
            mv "$SESSION_FILE.tmp" "$SESSION_FILE"
            echo -e "${GREEN}Session ID saved: $(cat $SESSION_FILE)${NC}"
        else
            rm -f "$SESSION_FILE.tmp"
        fi
    fi
    
    echo -e "${GREEN}Agent $AGENT_NAME completed${NC}"
}

# Run the agent
run_agent

# Show next steps
echo ""
echo "Next steps:"
echo "- View output: jq . $OUTPUT_FILE"
echo "- Continue session: $0 $AGENT_NAME --continue"
echo "- Continue with message: $0 $AGENT_NAME . 'new instructions'"
echo "- View logs: tail -f $LOG_FILE"