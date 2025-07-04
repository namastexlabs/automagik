# External Agents API Fix - Complete Solution

## Problem Summary
The API was creating `ClaudeCodeAgent` instead of external agent classes when handling requests to external agents like `flashinho_pro_external`.

## Root Cause
When `AgentFactory.create_agent()` couldn't find an agent in registered creators, it would fall back to dynamic imports. During this fallback, it would try `claude_code` framework, which has a generic `create_agent` function that always returns `ClaudeCodeAgent`.

## Fix Applied

### 1. Added Debug Logging
In `automagik/agents/models/agent_factory.py`, added logging to show which agents are available:
```python
# Log available creators for debugging
logger.debug(f"Looking for agent '{agent_type}' in {len(cls._agent_creators)} registered creators")
logger.debug(f"Available creators: {list(cls._agent_creators.keys())}")
```

### 2. Prevented Claude Code Fallback
Modified the dynamic import logic to only use `claude_code` framework when specifically requested:
```python
# IMPORTANT: Don't include claude_code for external agents - it should only be used for "claude_code" specifically
default_frameworks = ["pydanticai", "agno"]
# Only add claude_code if the agent_type is specifically "claude_code"
if agent_type == "claude_code":
    default_frameworks.append("claude_code")
```

### 3. Added Better Error Messages
When an agent isn't found, the error now shows available external agents:
```python
# Check if this might be an external agent that wasn't discovered
external_dir = os.environ.get("AUTOMAGIK_EXTERNAL_AGENTS_DIR")
if external_dir:
    logger.error(f"Agent '{agent_type}' not found. External agents directory is set to: {external_dir}")
    logger.error(f"Available external agents: {[k for k in cls._agent_creators.keys() if '.' not in k and k not in ['simple', 'claude_code']]}")
```

## Test Results

### Before Fix
```bash
curl -X POST http://localhost:58881/api/v1/agent/flashinho_pro_external/run \
  -H "X-API-Key: namastex888" -H "Content-Type: application/json" \
  -d '{"message_content": "Hello"}'
# Response: "Workflow 'surgeon' not found" (ClaudeCodeAgent error)
```

### After Fix
```bash
# Test script results:
✅ Successfully created agent: FlashinhoProExternalRefactored
✅ Agent is correctly identified as a Flashinho agent!
✅ API simulation successful - external agent created correctly!
```

## How It Works Now

1. **API receives request** for `flashinho_pro_external`
2. **AgentFactory checks registered creators** - finds it in the list
3. **Creates correct agent class** - `FlashinhoProExternalRefactored`
4. **No fallback to claude_code** - external agent is used as intended

## Files Modified

- `/automagik/agents/models/agent_factory.py` - Fixed create_agent logic

## Next Steps

1. **Test with actual API** - Start the API server and test the endpoints
2. **Verify all external agents** - Test all 4 Flashinho agents via API
3. **Monitor logs** - Watch for any edge cases or errors

## Commands to Test

```bash
# Start API server
source .venv/bin/activate
export AUTOMAGIK_EXTERNAL_AGENTS_DIR=./agents_examples
make dev

# Test external agent
curl -X POST http://localhost:8000/api/v1/agent/flashinho_pro_external/run \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"message_content": "Olá! Me ajuda com matemática?"}'

# Expected response: Flashinho agent response in Portuguese
```