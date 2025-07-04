# Automagik Agents Installation & Testing Guide

This guide will help you install and test Automagik Agents with the Flashinho external agent examples.

## Quick Installation

### 1. Install from Local Build

```bash
# Clone or navigate to the am-agents-labs directory
cd /path/to/am-agents-labs

# Create a virtual environment
python3 -m venv test_env
source test_env/bin/activate

# Install using uv (recommended) from local build
uv pip install -e .

# OR install using regular pip
pip install -e .
```

### 2. Set Up Environment Variables

Create a `.env` file in your project directory:

```bash
# Required API Keys
OPENAI_API_KEY=your-openai-key-here
GEMINI_API_KEY=your-gemini-key-here

# External Agent Directory (point to the examples)
AUTOMAGIK_EXTERNAL_AGENTS_DIR=./agents_examples

# API Configuration
AUTOMAGIK_API_KEY=namastex888
AUTOMAGIK_API_PORT=8000

# Database (SQLite by default)
AUTOMAGIK_DATABASE_TYPE=sqlite

# Optional: Flashinho-specific keys
FLASHED_API_KEY=your-flashed-key
FLASHED_API_URL=https://api.flashed.com
EVOLUTION_API_URL=https://evolution-api.com
```

## Testing Flashinho Agents

### 1. Start the API Server

```bash
# Make sure virtual environment is activated
source test_env/bin/activate

# Start the API server
automagik api
```

### 2. List Available Agents

```bash
# Check that Flashinho agents are discovered
curl -H "X-API-Key: namastex888" http://localhost:8000/api/v1/agent/list | jq
```

You should see agents like:
- `flashinho_pro`
- `flashinho_pro_external`
- `flashinho_the_first`

### 3. Test Simple Text Message

```bash
# Basic test
curl -X POST http://localhost:8000/api/v1/agent/flashinho_pro_external/run \
  -H "X-API-Key: namastex888" \
  -H "Content-Type: application/json" \
  -d '{
    "message_content": "Hello Flashinho!",
    "session_name": "test_session",
    "message_type": "text"
  }'
```

### 4. Test with Channel Payload (WhatsApp/Evolution)

Based on the Stan agent pattern, here are real-world payload examples:

#### Simple Evolution Payload
```bash
# Basic WhatsApp message through Evolution API
curl -X POST http://localhost:8000/api/v1/agent/flashinho_pro_external/run \
  -H "X-API-Key: namastex888" \
  -H "Content-Type: application/json" \
  -d '{
    "message_content": "I need help with math homework",
    "session_name": "whatsapp_5511999999999",
    "message_type": "text",
    "channel_type": "whatsapp",
    "user_id": "unique-user-123"
  }'
```

#### Complete Evolution Payload (Stan Pattern)
```bash
# Full WhatsApp payload with Evolution metadata
curl -X POST http://localhost:8000/api/v1/agent/flashinho_pro_external/run \
  -H "X-API-Key: namastex888" \
  -H "Content-Type: application/json" \
  -d '{
    "message_content": "Quero aprender matemática",
    "message_limit": 100,
    "user_id": "4f25505d-b707-4fe2-9a32-1db18683cf18",
    "message_type": "text",
    "session_name": "flashinho-prod-5511999999999",
    "channel_type": "whatsapp",
    "evolution_payload": {
      "data": {
        "key": {
          "remoteJid": "5511999999999@s.whatsapp.net",
          "fromMe": false,
          "id": "3EB0123456789ABCDEF"
        },
        "message": {
          "conversation": "Quero aprender matemática"
        },
        "messageType": "conversation",
        "pushName": "João Estudante",
        "owner": "flashinho-instance"
      },
      "instance": "flashinho-instance"
    }
  }'
```

#### Channel Payload Format (Alternative)
```bash
# Using channel_payload instead of evolution_payload
curl -X POST http://localhost:8000/api/v1/agent/flashinho_pro_external/run \
  -H "X-API-Key: namastex888" \
  -H "Content-Type: application/json" \
  -d '{
    "message_content": "Me ajuda com física?",
    "session_name": "whatsapp_session",
    "message_type": "text",
    "channel_payload": {
      "channel": "evolution",
      "instance": "agent",
      "phone_number": "5511999999999",
      "user_name": "Maria Silva",
      "message": {
        "key": {
          "remoteJid": "5511999999999@s.whatsapp.net",
          "fromMe": false,
          "id": "MSG123456"
        },
        "pushName": "Maria Silva",
        "message": {
          "conversation": "Me ajuda com física?"
        }
      },
      "event": "messages.upsert"
    }
  }'
```

### 5. Test with User Context

```bash
# Include user information for personalized responses
curl -X POST http://localhost:8000/api/v1/agent/flashinho_pro_external/run \
  -H "X-API-Key: namastex888" \
  -H "Content-Type: application/json" \
  -d '{
    "message_content": "What is my progress?",
    "session_name": "user_session",
    "message_type": "text",
    "user": {
      "email": "student@example.com",
      "phone_number": "+5511999999999",
      "name": "Test Student"
    }
  }'
```

### 6. Test Multimodal Content (Images)

```bash
# Send an image for analysis
curl -X POST http://localhost:8000/api/v1/agent/flashinho_pro_external/run \
  -H "X-API-Key: namastex888" \
  -H "Content-Type: application/json" \
  -d '{
    "message_content": "Can you help me solve this math problem?",
    "session_name": "multimodal_session",
    "message_type": "multimodal",
    "multimodal_content": {
      "images": [
        {
          "url": "https://example.com/math_problem.jpg",
          "detail": "high"
        }
      ]
    }
  }'
```

## Running Validation Tests

### 1. Basic Agent Tests

```bash
# Copy the test script
cat > test_flashinho.py << 'EOF'
#!/usr/bin/env python3
import os
import sys
import asyncio
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))
os.environ['AUTOMAGIK_EXTERNAL_AGENTS_DIR'] = './agents_examples'

async def test_flashinho():
    from automagik.agents.models.agent_factory import AgentFactory
    
    # Create Flashinho agent
    agent = AgentFactory.create_agent("flashinho_pro_external", {
        "model": "google:gemini-2.5-pro"
    })
    
    # Test basic interaction
    response = await agent.run("Hello! Can you introduce yourself?")
    print(f"Response: {response}")
    
    # Test with channel payload simulation
    channel_payload = {
        "channel": "evolution",
        "phone_number": "5511999999999",
        "user_name": "Test User"
    }
    
    response = await agent.process_message(
        "I need help with calculus",
        channel_payload=channel_payload
    )
    print(f"Channel response: {response}")

if __name__ == "__main__":
    asyncio.run(test_flashinho())
EOF

python test_flashinho.py
```

### 2. API Integration Test

```bash
# Test complete workflow
cat > test_api_workflow.py << 'EOF'
import requests
import json

API_URL = "http://localhost:8000"
API_KEY = "namastex888"
headers = {"X-API-Key": API_KEY, "Content-Type": "application/json"}

# 1. Create a session
session_data = {
    "message_content": "Start new learning session",
    "session_name": "learning_001",
    "message_type": "text",
    "user": {
        "email": "learner@test.com",
        "name": "Test Learner"
    }
}

print("1. Starting session...")
response = requests.post(
    f"{API_URL}/api/v1/agent/flashinho_pro_external/run",
    headers=headers,
    json=session_data
)
print(f"Session started: {response.status_code}")
session_id = response.json().get("session_id")

# 2. Continue conversation
followup_data = {
    "message_content": "I want to practice algebra",
    "session_id": session_id,
    "message_type": "text"
}

print("\n2. Following up...")
response = requests.post(
    f"{API_URL}/api/v1/agent/flashinho_pro_external/run",
    headers=headers,
    json=followup_data
)
print(f"Followup response: {response.json().get('message')[:100]}...")

print("\n✅ Workflow test complete!")
EOF

python test_api_workflow.py
```

## Understanding Flashinho Agent Structure

The Flashinho agents demonstrate:

1. **External Agent Pattern** - Located in `agents_examples/`
2. **Tool Integration** - Flashed and Evolution API tools
3. **Multi-Model Support** - Can use Gemini, GPT-4, etc.
4. **Channel Integration** - WhatsApp via Evolution API
5. **User Context** - Personalized responses based on user data

### Key Files to Examine

```bash
# Agent implementation
agents_examples/flashinho_pro_external/agent.py

# Prompts
agents_examples/flashinho_pro_external/prompts/prompt.py

# Tool implementations
agents_examples/tools/flashed/
agents_examples/tools/evolution/
```

## Troubleshooting

### Common Issues

1. **"No module named 'automagik'"**
   ```bash
   # Make sure you installed with -e flag
   pip install -e .
   ```

2. **"Agent not found"**
   ```bash
   # Check AUTOMAGIK_EXTERNAL_AGENTS_DIR is set correctly
   export AUTOMAGIK_EXTERNAL_AGENTS_DIR=./agents_examples
   ```

3. **API Connection Refused**
   ```bash
   # Make sure API server is running
   automagik api
   ```

4. **Missing API Keys**
   ```bash
   # Check .env file has required keys
   cat .env | grep API_KEY
   ```

## Next Steps

1. **Modify Flashinho** - Try changing prompts in `agents_examples/flashinho_*/prompts/`
2. **Create Your Own** - Copy a Flashinho example and customize
3. **Add Tools** - Create new tools in `agents_examples/tools/`
4. **Test Production** - Deploy with PostgreSQL instead of SQLite

For more examples, check the test files:
- `test_external_agents.py` - Unit tests
- `test_external_api.py` - API integration tests