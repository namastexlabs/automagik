# Manual Test Commands for Claude Code API

After restarting your server, use these commands to test the updated API.

## Prerequisites
```bash
# Make sure the server is running
# Default API key: namastex888
# Default port: 28881
```

## 1. Quick Health Check
```bash
curl -X GET "http://localhost:28881/api/v1/agent/claude-code/health" \
  -H "x-api-key: namastex888" | jq '.'
```

## 2. List Available Workflows
```bash
curl -X GET "http://localhost:28881/api/v1/agent/claude-code/workflows" \
  -H "x-api-key: namastex888" | jq '.'
```

## 3. Test Minimal Payload (Current Branch Auto-Detection)
```bash
# This will use your current git branch automatically
curl -X POST "http://localhost:28881/api/v1/agent/claude-code/run" \
  -H "x-api-key: namastex888" \
  -H "Content-Type: application/json" \
  -d @payloads/minimal_test.json | jq '.'
```

## 4. Test Full Payload (All Parameters)
```bash
curl -X POST "http://localhost:28881/api/v1/agent/claude-code/run" \
  -H "x-api-key: namastex888" \
  -H "Content-Type: application/json" \
  -d @payloads/full_test.json | jq '.'
```

## 5. Test Branch Auto-Detection
```bash
# This will show which branch Claude is working on
curl -X POST "http://localhost:28881/api/v1/agent/claude-code/run" \
  -H "x-api-key: namastex888" \
  -H "Content-Type: application/json" \
  -d @payloads/branch_detect_test.json | jq '.'
```

## 6. Test External Repository
```bash
# This will clone and analyze an external repo
curl -X POST "http://localhost:28881/api/v1/agent/claude-code/run" \
  -H "x-api-key: namastex888" \
  -H "Content-Type: application/json" \
  -d @payloads/external_repo_test.json | jq '.'
```

## 7. Check Run Status (Replace RUN_ID)
```bash
# Get the run_id from any of the above commands
RUN_ID="run_XXXXXXXXXX"  # Replace with actual run_id

curl -X GET "http://localhost:28881/api/v1/run/$RUN_ID/status" \
  -H "x-api-key: namastex888" | jq '.'
```

## 8. Quick One-Liner Tests

### Test with inline JSON (minimal)
```bash
curl -X POST "http://localhost:28881/api/v1/agent/claude-code/run" \
  -H "x-api-key: namastex888" \
  -H "Content-Type: application/json" \
  -d '{"workflow_name":"test","message":"List your top 3 tools","max_turns":1}' | jq '.'
```

### Test specific branch
```bash
curl -X POST "http://localhost:28881/api/v1/agent/claude-code/run" \
  -H "x-api-key: namastex888" \
  -H "Content-Type: application/json" \
  -d '{"workflow_name":"test","message":"What branch am I on?","max_turns":1,"git_branch":"develop"}' | jq '.'
```

### Test with custom timeout
```bash
curl -X POST "http://localhost:28881/api/v1/agent/claude-code/run" \
  -H "x-api-key: namastex888" \
  -H "Content-Type: application/json" \
  -d '{"workflow_name":"test","message":"Analyze the codebase structure","max_turns":5,"timeout":1800}' | jq '.'
```

## 9. Run All Tests Script
```bash
# Make the script executable if needed
chmod +x test_claude_code_api.sh

# Run all tests
./test_claude_code_api.sh
```

## Expected Behaviors

1. **No git_branch specified** → Uses current git branch
2. **No repository_url specified** → Uses current repository
3. **Status endpoint** → Now includes logs (last 1000 lines)
4. **No x-api-key parameters** → Only header authentication required
5. **workflow_name in body** → Not in URL path anymore

## Troubleshooting

If you get authentication errors:
```bash
# Make sure you're using the correct API key
# Check your .env file for AM_API_KEY value
```

If you get 404 errors:
```bash
# Old endpoints that no longer exist:
# ❌ POST /agent/claude-code/test/run (workflow in path)
# ❌ GET /agent/claude-code/run/RUN_ID/logs
# ❌ GET /agent/claude-code/logs

# New endpoints:
# ✅ POST /agent/claude-code/run (workflow in body)
# ✅ GET /run/RUN_ID/status (includes logs)
```

If you don't have jq installed:
```bash
# Remove "| jq '.'" from commands, or install jq:
# Ubuntu/Debian: sudo apt-get install jq
# Mac: brew install jq
```