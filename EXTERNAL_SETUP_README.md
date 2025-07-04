# Quick Setup Guide for External Users

This guide helps you set up and test Automagik Agents from a local build.

## 1. Installation (2 minutes)

```bash
# Navigate to am-agents-labs directory
cd /path/to/am-agents-labs

# Create and activate virtual environment
python3 -m venv my_test_env
source my_test_env/bin/activate

# Install from local build using uv (faster)
uv pip install -e .

# OR using regular pip
pip install -e .
```

## 2. Basic Configuration (1 minute)

Create a `.env` file:

```bash
# Minimum required
OPENAI_API_KEY=your-key-here
AUTOMAGIK_EXTERNAL_AGENTS_DIR=./agents_examples
```

## 3. Test External Agents (1 minute)

```bash
# Run the simple test script
python test_flashinho_simple.py
```

Expected output:
```
✅ Automagik is installed
✅ Created agent: FlashinhoProExternalRefactored
✅ Agent responded: Olá! Claro que posso te ajudar...
✅ All tests passed!
```

## 4. Start API Server

```bash
# In one terminal
automagik api

# In another terminal, test the API
curl -X POST http://localhost:8000/api/v1/agent/flashinho_pro_external/run \
  -H "X-API-Key: namastex888" \
  -H "Content-Type: application/json" \
  -d '{"message_content": "Hello!"}'
```

## 5. Test WhatsApp Integration

Example with channel payload:

```python
import requests

# WhatsApp-style message
payload = {
    "message_content": "Oi, preciso de ajuda",
    "session_name": "whatsapp_5511999999999",
    "channel_type": "whatsapp",
    "evolution_payload": {
        "data": {
            "key": {
                "remoteJid": "5511999999999@s.whatsapp.net",
                "fromMe": False,
                "id": "MSG123"
            },
            "pushName": "João Silva",
            "message": {
                "conversation": "Oi, preciso de ajuda"
            }
        },
        "instance": "my-instance"
    }
}

response = requests.post(
    "http://localhost:8000/api/v1/agent/flashinho_pro_external/run",
    headers={"X-API-Key": "namastex888"},
    json=payload
)

print(response.json())
```

## Available External Agents

After installation, these agents are available:
- `flashinho_pro` - Professional Flashinho with Gemini
- `flashinho_pro_external` - External version example
- `flashinho_the_first` - Original Flashinho
- `flashinho_old_make` - Legacy compatibility version

## Troubleshooting

### "Module not found" error
```bash
# Make sure virtual environment is activated
which python  # Should show my_test_env/bin/python
```

### "Agent not found" error
```bash
# Check environment variable
echo $AUTOMAGIK_EXTERNAL_AGENTS_DIR  # Should show ./agents_examples
```

### API not responding
```bash
# Check if server is running
curl http://localhost:8000/health
```

## Next Steps

1. **Explore agents**: Look at `agents_examples/flashinho_*/agent.py`
2. **Modify prompts**: Edit files in `agents_examples/flashinho_*/prompts/`
3. **Create your own**: Copy any flashinho example and customize
4. **Add tools**: See `agents_examples/tools/` for examples

## Complete Working Example

```python
# example_usage.py
import asyncio
from automagik.agents.models.agent_factory import AgentFactory

async def main():
    # Create agent
    agent = AgentFactory.create_agent("flashinho_pro_external", {
        "model": "openai:gpt-4o-mini"
    })
    
    # Send message
    response = await agent.run("Help me learn Python")
    print(response)

asyncio.run(main())
```

That's it! You now have a working Automagik Agents installation with external agents.