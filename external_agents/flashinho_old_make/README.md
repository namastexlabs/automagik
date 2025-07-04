# Flashinho Old Make - External Agent

This is the Flashinho Old Make agent converted to the new simplified external agent pattern.

## 🚀 Features

- Educational coaching agent for Brazilian students
- Portuguese language (Gen Z style)
- Integration with Flashed educational platform
- Student engagement and re-engagement strategies
- Academic support across high school subjects

## 📁 Structure

```
flashinho_old_make/
├── agent.py            # Main agent class (no create_agent needed!)
├── prompt.md           # Agent prompt in Markdown format
├── .env.example        # Example environment variables
└── README.md           # This file
```

## 🔧 Configuration

1. Copy `.env.example` to `.env` and set your API key:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and add your Flashed API key:
   ```
   FLASHED_API_KEY=your_actual_api_key_here
   ```

## 🎯 Usage

The agent will be automatically discovered when you set:
```bash
export AUTOMAGIK_EXTERNAL_AGENTS_DIR=/path/to/external_agents
```

Then it can be used via the API or CLI:
```bash
automagik agents chat -a flashinho_old_make
```

## 📝 Key Improvements

This external agent demonstrates the new simplified pattern:
- ✅ No `create_agent` function needed
- ✅ No factory boilerplate
- ✅ Direct class discovery by AgentFactory
- ✅ Automatic database registration at API startup
- ✅ Package-specific .env file support
- ✅ External API key registration
- ✅ Prompt loaded from `prompt.md` file (no Python needed!)

## 🤖 Agent Details

- **Model**: `openai:gpt-4o-mini` (can be changed via API)
- **Language**: Portuguese (pt-BR)
- **Supported Media**: Images, Audio, Documents
- **Target Users**: Brazilian high school students

## 🔗 Tools

The agent uses centralized tools that are registered via the tool_registry. The Flashed-specific tools include:
- User data retrieval
- Score tracking
- Learning roadmap management
- Objectives tracking
- Study round history
- Energy system management

All tools are managed centrally to avoid code duplication across agents.