# Session Memory Fix - Migration Guide for External Agents

## Issue Fixed in v0.6.14

Version 0.6.13 had a critical bug where agents could not access previous messages in the same session. This has been fixed in v0.6.14.

## For External Agent Developers

### 1. Update Your Dependencies

Update your `pyproject.toml` or `requirements.txt`:

```toml
# pyproject.toml
[tool.poetry.dependencies]
automagik = ">=0.6.14"

# or for pip
automagik>=0.6.14
```

### 2. Reinstall Your Package

```bash
# Clear cache and reinstall
pip cache purge
pip install --upgrade automagik>=0.6.14

# Or with uv
uv cache clean
uv sync --refresh
```

### 3. Verify the Fix

Run this test to confirm memory is working:

```python
import asyncio
from your_agent import YourAgent
from automagik.memory import MessageHistory

async def test_memory():
    agent = YourAgent()
    session_id = "test-session"
    message_history = MessageHistory(session_id=session_id)
    
    # First message
    response1 = await agent.process_message(
        "My name is Alice",
        session_id=session_id,
        message_history=message_history
    )
    print(f"Response 1: {response1}")
    
    # Second message - should remember
    response2 = await agent.process_message(
        "What's my name?",
        session_id=session_id,
        message_history=message_history
    )
    print(f"Response 2: {response2}")
    
    # Check if "Alice" is in response2
    assert "Alice" in response2, "Memory not working!"
    print("✅ Memory test passed!")

asyncio.run(test_memory())
```

## What Was Fixed

- **Root Cause**: Each message in a session was creating a new user_id
- **Fix**: Sessions now maintain consistent user_id across all messages
- **Result**: Agents can now access full conversation history

## Troubleshooting

If memory still doesn't work after updating:

1. **Check Version**: Ensure you're actually using 0.6.14+
   ```bash
   pip show automagik | grep Version
   ```

2. **Check Logs**: Look for these log messages:
   ```
   ✅ Using existing session {session_id} with user_id {user_id} from session
   ✅ Loaded {N} messages from session history
   ```

3. **Verify Session Name**: Ensure you're using consistent session names across requests

4. **Check MessageHistory**: Ensure you're passing the MessageHistory object to process_message()

## Need Help?

If you're still experiencing issues after upgrading to 0.6.14+, please:
1. Check the logs for error messages
2. Verify you're passing MessageHistory correctly
3. Open an issue with reproduction steps