  #!/bin/bash
  echo "🚀 Testing Claude Code API Fixes..."

  # Test 1: Start execution
  echo "📝 Starting test execution..."
  RESPONSE=$(curl -s -X POST "http://localhost:28881/api/v1/agent/claude-code/run" \
  -H "Content-Type: application/json" \
  -H "x-api-key: namastex888" \
  -d '{
    "workflow_name": "test",
    "message": "List your top 3 tools and explain how you would use each one",
    "session_id": "test-comprehensive-check",
    "max_turns": 5,
    "git_branch": "main"
  }')

  echo "✅ First Response:"
  echo "$RESPONSE" | jq .

  # Extract run_id
  RUN_ID=$(echo "$RESPONSE" | jq -r '.run_id')
  echo "📋 Run ID: $RUN_ID"

  # Test 2: Check status immediately
  echo "⏱️ Checking status immediately..."
  curl -s -X GET "http://localhost:28881/api/v1/agent/claude-code/run/$RUN_ID/status" \
  -H "x-api-key: namastex888" | jq '{status: .status, execution_time: .execution_time, has_result: (.result != null)}'

  # Test 3: Wait and check again
  echo "⏳ Waiting 10 seconds then checking again..."
  sleep 10
  curl -s -X GET "http://localhost:28881/api/v1/agent/claude-code/run/$RUN_ID/status" \
  -H "x-api-key: namastex888" | jq '{
    status: .status, 
    execution_time: .execution_time, 
    result_length: (.result // "" | length),
    git_commits: (.git_commits | length)
  }'

  echo "🎉 Test completed!"
