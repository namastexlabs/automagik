# Flashinho Old Make Agent

Basic educational assistant for Brazilian students, integrated with the Flashed learning platform.

## Features

- Brazilian Portuguese educational assistance
- Flashed API integration for user data and gamification
- Multimodal support (images, audio, documents)
- Basic educational content generation

## Configuration

The agent uses OpenAI GPT-4o-mini as the default model and requires:

- `OPENAI_API_KEY` environment variable
- Flashed API access for user data integration

## Tools

### Flashed API Tools
- `get_user_data` - Get user profile information
- `get_user_score` - Get user progress and energy
- `get_user_roadmap` - Get study roadmap
- `get_user_objectives` - Get learning objectives
- `get_last_card_round` - Get last study session data
- `get_user_energy` - Get current energy level

## Usage

```python
from agents_examples.flashinho_old_make import FlashinhoOldMakeAgent

agent = FlashinhoOldMakeAgent(config={
    "model": "openai:gpt-4o-mini",
    "temperature": 0.7
})

response = await agent.run("Olá! Como posso ajudar com seus estudos?")
```

## Client-Specific Features

This agent is designed for Brazilian educational platform integration and includes:

- Generation Z communication style
- Gaming elements integration
- Portuguese language optimization
- Educational content focus