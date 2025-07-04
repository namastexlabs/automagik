# 🤖 External Agents Examples

This directory contains working examples of external agents that have been successfully tested with the Automagik platform.

## 🚀 Quick Start - Reduced Boilerplate

### Method 1: Using BaseExternalAgent (Recommended)

The simplest way to create an external agent with minimal boilerplate:

```python
from base_external_agent import BaseExternalAgent
from tools import get_user_data, get_user_score

class MyAgent(BaseExternalAgent):
    # Just set these class attributes - no boilerplate needed!
    DEFAULT_MODEL = "openai:gpt-4o-mini"
    EXTERNAL_API_KEYS = [("MY_API_KEY", "My API key")]
    EXTERNAL_URLS = [("MY_API_URL", "My API URL")]
    
    def _initialize_agent(self):
        self._code_prompt_text = "You are a helpful assistant..."
        self.tool_registry.register_tool(get_user_data)
```

### Method 2: Using Tool Decorators

Create tools with minimal code:

```python
from tool_utils import external_tool

@external_tool(description="Get weather data")
async def get_weather(city: str, context: dict) -> dict:
    return {"temperature": 25, "condition": "sunny"}
```

## 📁 Improved Structure

```
agents_examples/
├── tools/                    # Shared tools - no duplication!
│   ├── flashed/             # Educational platform tools
│   └── evolution/           # Messaging tools
├── utils/                    # Shared utilities
│   ├── user_matcher.py      # User matching utilities
│   └── memory_manager.py    # Memory management
├── base_external_agent.py    # Base class - handles all boilerplate
├── external_agent_factory.py # Factory with error handling
├── tool_utils.py            # Tool creation utilities
└── your_agent/              # Your agent - just the essentials
    ├── agent.py             # ~30 lines instead of ~100
    └── prompts/             # Your prompts
```

## ✅ Available Agent Examples

### `flashinho_pro_external/`

**Status**: ✅ **FULLY TESTED AND WORKING**

This is a complete external agent implementation that demonstrates:

- ✅ **Agent Discovery**: Automatically discovered by Automagik server
- ✅ **Database Integration**: Registered in database with ID assignment
- ✅ **API Integration**: Accessible via `/api/v1/agent/flashinho_pro_external/run`
- ✅ **Real AI Execution**: Tested with OpenAI GPT-4.1 API
- ✅ **Session Management**: Creates and manages user sessions
- ✅ **Error Handling**: Graceful error responses in Portuguese
- ✅ **Tool Integration**: Includes Flashed API and Evolution API tools

### `flashinho_old_make/`

**Status**: 🔄 **CLIENT-SPECIFIC AGENT (MIGRATED)**

Basic educational assistant for Brazilian students:

- 🎯 **Basic Features**: Educational assistance and Flashed API integration
- 🔧 **Model**: OpenAI GPT-4o-mini
- 📚 **Tools**: Core Flashed API tools for user data and gamification
- 🇧🇷 **Language**: Brazilian Portuguese, Generation Z style

### `flashinho_pro/`

**Status**: 🔄 **CLIENT-SPECIFIC AGENT (MIGRATED)**

Advanced multimodal educational assistant:

- 🚀 **Advanced Features**: Multimodal processing, Pro subscription features
- 🔧 **Model**: Google Gemini 2.5 Pro
- 📸 **Capabilities**: Image analysis, educational problem solving
- 🔗 **Integration**: Full Flashed + Evolution API integration
- 💬 **Messaging**: Real-time messaging and workflow orchestration

### `flashinho_the_first/`

**Status**: 🔄 **CLIENT-SPECIFIC AGENT (MIGRATED)**

Most comprehensive educational platform integration:

- 🌟 **Full-Featured**: Complete educational platform integration
- 🧠 **Dynamic**: Pro vs Free user differentiation
- 🔄 **Smart**: User identification and session management
- 📊 **Analytics**: Comprehensive user progress tracking
- 🎨 **Customizable**: Multiple prompt configurations

## 🚀 How to Use These Examples

### 1. **Setup Directory Structure**
```bash
# In your project root, create:
mkdir -p automagik_agents

# Copy the example:
cp -r /path/to/am-agents-labs/agents_examples/flashinho_pro_external automagik_agents/
```

### 2. **Environment Configuration**
```env
# In your .env file:
AUTOMAGIK_EXTERNAL_AGENTS_DIR=./automagik_agents

# Required API keys:
OPENAI_API_KEY=your_openai_key
GEMINI_API_KEY=your_gemini_key
ANTHROPIC_API_KEY=your_anthropic_key

# Optional service keys (for tools):
FLASHED_API_KEY=your_flashed_key
EVOLUTION_API_KEY=your_evolution_key
```

### 3. **Start Server**
```bash
# Activate your environment
source venv/bin/activate

# Start the server
automagik-server --port 18881
```

### 4. **Verify External Agent**
```bash
# Check agent is discovered
curl -H "X-API-Key: your_api_key" http://localhost:18881/api/v1/agent/list | grep flashinho_pro_external

# Test execution
curl -X POST http://localhost:18881/api/v1/agent/flashinho_pro_external/run \
  -H "X-API-Key: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{"message_content": "Olá! Como você está?", "session_name": "test"}'
```

## 📋 Testing Results

**Last Tested**: 2025-07-03  
**Environment**: Python 3.12, Automagik v0.4.0  
**API**: OpenAI GPT-4.1  

**Results**:
- ✅ Server startup: **SUCCESS**
- ✅ Agent discovery: **SUCCESS** (14 total agents: 13 built-in + 1 external)
- ✅ Database registration: **SUCCESS** (Agent ID: 14)
- ✅ API execution: **SUCCESS** (200 OK responses)
- ✅ Real AI responses: **SUCCESS** (Token usage: ~1700 tokens)
- ✅ Session management: **SUCCESS** (UUID session tracking)

## 🔧 External Agent Development

Use this example as a template for creating your own external agents:

1. **Copy Structure**: Use `flashinho_pro_external/` as your starting point
2. **Customize Agent**: Modify `agent.py` with your agent logic
3. **Update Prompts**: Edit files in `prompts/` directory
4. **Add Tools**: Create new tools in `tools/` directory
5. **Test Integration**: Follow the testing steps above

## 📚 Key Files

- `__init__.py` - Agent factory function and exports
- `agent.py` - Main agent implementation
- `prompts/prompt.py` - Agent system prompts
- `tools/` - External API integrations and tools
- `README.md` - Agent-specific documentation

## 🎯 Success Criteria

Your external agent is working correctly when:

1. ✅ Server logs show "✅ Discovered external agent: your_agent_name"
2. ✅ Agent appears in `/api/v1/agent/list` endpoint
3. ✅ Agent responds to `/api/v1/agent/your_agent_name/run` requests
4. ✅ Database shows agent with assigned ID
5. ✅ Real API responses with token usage tracking

---

**Happy Agent Development!** 🚀