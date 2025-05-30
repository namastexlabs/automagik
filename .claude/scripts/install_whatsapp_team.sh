#!/bin/bash
# install_whatsapp_team.sh - Setup the WhatsApp-integrated agent team

set -euo pipefail

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}=== WhatsApp Agent Team Setup ===${NC}"
echo ""

# Check if we're in the right directory
if [[ ! -d ".claude" ]]; then
    echo -e "${RED}Error: Must run from project root (where .claude directory exists)${NC}"
    exit 1
fi

# Create directory structure
echo -e "${BLUE}Creating directory structure...${NC}"
mkdir -p .claude/scripts/agent-scripts
mkdir -p .claude/logs
mkdir -p .claude/sessions
mkdir -p .claude/archives

# Create agent runner scripts
echo -e "${BLUE}Creating agent runner scripts...${NC}"

# List of scripts to create
SCRIPTS=(
    "run_alpha.sh"
    "run_beta.sh"
    "run_delta.sh"
    "run_epsilon.sh"
    "run_gamma.sh"
)

# Check if scripts already exist
EXISTING_SCRIPTS=0
for script in "${SCRIPTS[@]}"; do
    if [[ -f ".claude/scripts/agent-scripts/$script" ]]; then
        ((EXISTING_SCRIPTS++))
    fi
done

if [[ $EXISTING_SCRIPTS -eq ${#SCRIPTS[@]} ]]; then
    echo -e "${GREEN}✓ All agent scripts already exist${NC}"
else
    echo -e "${YELLOW}⚠️  Agent scripts missing. Please create:${NC}"
    for script in "${SCRIPTS[@]}"; do
        if [[ ! -f ".claude/scripts/agent-scripts/$script" ]]; then
            echo "   - .claude/scripts/agent-scripts/$script"
        fi
    done
    echo ""
    echo "Copy the script contents from the artifacts provided."
fi

# Make scripts executable
echo -e "${BLUE}Making scripts executable...${NC}"
chmod +x .claude/scripts/*.sh 2>/dev/null || true
chmod +x .claude/scripts/agent-scripts/*.sh 2>/dev/null || true

# Check for agent prompts
echo -e "${BLUE}Checking agent prompts...${NC}"
PROMPTS=(
    "alpha_prompt.md"
    "beta_prompt.md"
    "delta_prompt.md"
    "epsilon_prompt.md"
    "gamma_prompt.md"
)

MISSING_PROMPTS=0
for prompt in "${PROMPTS[@]}"; do
    if [[ ! -f ".claude/agents-prompts/$prompt" ]]; then
        echo -e "${YELLOW}⚠️  Missing: .claude/agents-prompts/$prompt${NC}"
        ((MISSING_PROMPTS++))
    fi
done

if [[ $MISSING_PROMPTS -eq 0 ]]; then
    echo -e "${GREEN}✓ All agent prompts found${NC}"
else
    echo -e "${RED}Create the missing prompts from the artifacts provided${NC}"
fi

# Test WhatsApp connection
echo ""
echo -e "${BLUE}Testing WhatsApp connection...${NC}"
WHATSAPP_URL="http://192.168.112.142:8080/message/sendText/SofIA"
WHATSAPP_GROUP="120363404050997890@g.us"
WHATSAPP_KEY="namastex888"

if curl -s -X POST "$WHATSAPP_URL" \
    -H "Content-Type: application/json" \
    -H "apikey: $WHATSAPP_KEY" \
    -d "{\"number\": \"$WHATSAPP_GROUP\", \"text\": \"🚀 Agent team setup complete! Ready for orchestration.\"}" > /dev/null; then
    echo -e "${GREEN}✓ WhatsApp connection successful${NC}"
else
    echo -e "${RED}✗ WhatsApp connection failed${NC}"
    echo "Check your WhatsApp configuration"
fi

# Summary
echo ""
echo -e "${GREEN}=== Setup Summary ===${NC}"
echo ""
echo "Directory structure: ✓"
echo "Scripts location: .claude/scripts/"
echo "Agent scripts: .claude/scripts/agent-scripts/"
echo "Prompts location: .claude/agents-prompts/"
echo ""

if [[ $EXISTING_SCRIPTS -eq ${#SCRIPTS[@]} ]] && [[ $MISSING_PROMPTS -eq 0 ]]; then
    echo -e "${GREEN}✅ Setup complete! You're ready to start.${NC}"
    echo ""
    echo "To begin orchestration:"
    echo -e "${BLUE}cd .claude/scripts${NC}"
    echo -e "${BLUE}./run_team.sh \"Your Epic Name\" 123${NC}"
else
    echo -e "${YELLOW}⚠️  Setup incomplete. Please:${NC}"
    echo "1. Create missing agent scripts in .claude/scripts/agent-scripts/"
    echo "2. Create missing prompts in .claude/agents-prompts/"
    echo "3. Run this script again to verify"
fi

echo ""
echo -e "${BLUE}Documentation:${NC} See WhatsApp-Integrated Team Workflow Summary"