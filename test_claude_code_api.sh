#!/bin/bash
# Test script for Claude Code API after cleanup

API_KEY="namastex888"
BASE_URL="http://localhost:28881/api/v1"

echo "🧪 Testing Claude Code API..."
echo "================================"

# 1. Test Health Check
echo -e "\n1️⃣ Health Check:"
curl -X GET "$BASE_URL/agent/claude-code/health" \
  -H "x-api-key: $API_KEY" | jq '.'

# 2. List Workflows
echo -e "\n\n2️⃣ List Workflows:"
curl -X GET "$BASE_URL/agent/claude-code/workflows" \
  -H "x-api-key: $API_KEY" | jq '.'

# 3. Run Test Workflow (minimal payload)
echo -e "\n\n3️⃣ Running Test Workflow (minimal payload):"
RUN_RESPONSE=$(curl -X POST "$BASE_URL/agent/claude-code/run" \
  -H "x-api-key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_name": "test",
    "message": "Hello! List your top 3 tools with brief descriptions",
    "max_turns": 1
  }')

echo "$RUN_RESPONSE" | jq '.'

# Extract run_id
RUN_ID=$(echo "$RUN_RESPONSE" | jq -r '.run_id')
echo "Run ID: $RUN_ID"

# 4. Wait and check status
echo -e "\n\n4️⃣ Waiting 10 seconds before checking status..."
sleep 10

echo "Getting status for run: $RUN_ID"
curl -X GET "$BASE_URL/run/$RUN_ID/status" \
  -H "x-api-key: $API_KEY" | jq '.'

# 5. Test with all optional parameters
echo -e "\n\n5️⃣ Running Test with All Parameters:"
FULL_RUN=$(curl -X POST "$BASE_URL/agent/claude-code/run" \
  -H "x-api-key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_name": "test",
    "message": "What tools do you have for file manipulation? List the top 3.",
    "max_turns": 2,
    "repository_url": "https://github.com/namastexlabs/am-agents-labs.git",
    "git_branch": "main",
    "timeout": 3600,
    "session_name": "test-file-tools"
  }')

echo "$FULL_RUN" | jq '.'
FULL_RUN_ID=$(echo "$FULL_RUN" | jq -r '.run_id')

echo -e "\n\n6️⃣ Test branch auto-detection (no git_branch specified):"
BRANCH_TEST=$(curl -X POST "$BASE_URL/agent/claude-code/run" \
  -H "x-api-key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_name": "test",
    "message": "What git branch are you currently on? Use git commands to check.",
    "max_turns": 1
  }')

echo "$BRANCH_TEST" | jq '.'

echo -e "\n\n✅ Test script complete!"
echo "================================"