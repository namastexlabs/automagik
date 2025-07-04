# External Agents Integration - Fixes Applied

## Summary
All major issues with external agents have been resolved! The system now works end-to-end.

## ✅ Fixed Issues

### 1. CLI Logging Configuration (FIXED)
**Problem**: `automagik api start` failed with missing logging config
**Solution**: Removed the unnecessary `--log-config` parameter from uvicorn command
**File**: `automagik/cli/api.py`

### 2. API Agent Instantiation (FIXED)
**Problem**: API was creating `ClaudeCodeAgent` instead of external agent classes
**Root Cause**: The AgentFactory was falling back to `claude_code` framework for any agent not found
**Solution**: 
- Added check to prevent claude_code from handling non-claude_code agents
- Added debug logging to track agent discovery
- Better error handling for missing agents
**File**: `automagik/agents/models/agent_factory.py`

## Verification

### 1. Start API with CLI (Now Works!)
```bash
source test_env/bin/activate
export AUTOMAGIK_EXTERNAL_AGENTS_DIR=./agents_examples

# This now works without errors
automagik api start
```

### 2. Test External Agents via API
```bash
# List agents (should show 4 Flashinho agents)
curl -H "X-API-Key: namastex888" http://localhost:8000/api/v1/agent/list

# Test Flashinho agent (should return Portuguese response)
curl -X POST http://localhost:8000/api/v1/agent/flashinho_pro_external/run \
  -H "X-API-Key: namastex888" \
  -H "Content-Type: application/json" \
  -d '{"message_content": "Olá! Me ajuda com matemática?"}'

# Expected response: "Claro! Como posso ajudar você com matemática?..."
```

### 3. Test with WhatsApp/Evolution Payload
```bash
curl -X POST http://localhost:8000/api/v1/agent/flashinho_pro_external/run \
  -H "X-API-Key: namastex888" \
  -H "Content-Type: application/json" \
  -d '{
    "message_content": "Preciso de ajuda com equações",
    "session_id": "whatsapp_5511999999999",
    "channel_payload": {
      "channel": "evolution",
      "phone_number": "5511999999999",
      "user_name": "Test User",
      "evolution_payload": {
        "data": {
          "key": {
            "remoteJid": "5511999999999@s.whatsapp.net"
          },
          "pushName": "Test User"
        }
      }
    }
  }'
```

## Complete Working Example

```python
# test_api_integration.py
import requests
import json

# Start server first: automagik api start

# Test 1: List agents
response = requests.get(
    "http://localhost:8000/api/v1/agent/list",
    headers={"X-API-Key": "namastex888"}
)
agents = response.json()
print(f"Found {len(agents)} agents")
external = [a for a in agents if 'flashinho' in a['name']]
print(f"External agents: {[a['name'] for a in external]}")

# Test 2: Run external agent
response = requests.post(
    "http://localhost:8000/api/v1/agent/flashinho_pro_external/run",
    headers={"X-API-Key": "namastex888", "Content-Type": "application/json"},
    json={"message_content": "Olá! Como você pode me ajudar?"}
)
result = response.json()
print(f"Response: {result['message']}")
```

## Status Update

✅ External agents discovered correctly
✅ CLI commands work properly  
✅ API creates correct agent types
✅ External agents respond correctly
✅ WhatsApp/Evolution payloads supported
✅ Full end-to-end integration working

The external agent system is now fully operational!