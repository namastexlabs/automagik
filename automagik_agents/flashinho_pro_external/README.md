# Flashinho Pro External Agent

This is an external version of the Flashinho Pro agent that can be loaded by Automagik without being in the source code.

## Structure

```
flashinho_pro_external/
├── __init__.py           # Factory function create_agent()
├── agent.py              # Main agent class
├── prompts/              # Agent prompts
│   ├── __init__.py
│   └── prompt.py         # AGENT_PROMPT and AGENT_FREE
├── tools/                # Self-contained tools
│   ├── __init__.py
│   ├── flashed/          # Flashed API tools
│   └── evolution/        # Evolution API tools
└── README.md             # This file
```

## Features

- **Multimodal Support**: Analyzes images, audio, and documents for educational content
- **Dynamic Model Selection**: Uses Gemini 2.5 Pro for Pro users, Gemini 2.5 Flash for free users
- **Flashed API Integration**: Complete integration with educational gaming features
- **WhatsApp/Evolution Support**: Sends messages via Evolution API
- **Brazilian Portuguese**: Optimized for Brazilian high school students

## Requirements

Environment variables needed:
- `GEMINI_API_KEY`: Google Gemini API key
- `FLASHED_API_KEY`: Flashed API authentication
- `FLASHED_API_URL`: Flashed API endpoint
- `EVOLUTION_API_KEY`: Evolution API key (optional)
- `EVOLUTION_API_URL`: Evolution API URL (optional)

## Usage

1. Place this directory in your `automagik_agents` folder (or set `AUTOMAGIK_EXTERNAL_AGENTS_DIR`)
2. Start the Automagik server
3. The agent will be automatically discovered and available as "flashinho_pro_external"

## Testing

```bash
# Test via API
curl -X POST http://localhost:8000/api/v1/agent/flashinho_pro_external/run \
  -H "X-API-Key: namastex888" \
  -H "Content-Type: application/json" \
  -d '{"message_content": "Olá Flashinho!", "session_name": "test"}'
```

## Notes

- This is a simplified version focused on demonstrating external agent loading
- All tools are self-contained within the agent directory
- Memory management features are simplified compared to the full version