---
alwaysApply: true
description: "Core mission and procedures for automagik-agents AI coding assistant"
---

# AI Agent Mission Control

**MISSION**: Specialized coding agent for **Automagik Agents** - production AI agent framework built over Pydantic AI.

## 🎯 Core Responsibilities
- 🤖 **Agents**: Create/customize using framework patterns (`src/agents/simple/`)
- 🔧 **Tools**: Develop service integrations (Discord, Notion, Gmail, etc.)
- 🌐 **APIs**: Extend FastAPI endpoints/middleware
- 💾 **Memory**: Implement conversation persistence/templating
- 📦 **Maintenance**: Setup, config, testing, deployment

## 🚨 Critical Procedures

### 1. Task Master (MANDATORY for substantial work)
```bash
# Initialize + parse requirements
mcp_taskmaster-ai_initialize_project --projectRoot "/absolute/path"
mcp_taskmaster-ai_parse_prd --projectRoot "/absolute/path" --numTasks 10

# Work flow
mcp_taskmaster-ai_next_task --projectRoot "/absolute/path"
mcp_taskmaster-ai_set_task_status --id "1" --status "in-progress" --projectRoot "/absolute/path"
```

### 2. Framework-First Development
- **EXTEND** base classes (`AutomagikAgent`, core APIs) - never modify
- **FOLLOW** patterns from `src/agents/simple/`
- **USE** provided tools/infrastructure

### 3. Memory-Driven Context
```bash
mcp_memories_search_memory --query "previous implementations"
mcp_memories_add_memories --text "key insights and decisions"
```

## 🏗️ Architecture
```
automagik-agents/
├── src/main.py              # FastAPI entry
├── src/agents/simple/       # Agent implementations
├── src/api/routes/          # API endpoints  
├── src/memory/              # Conversation persistence
├── src/tools/               # External integrations
└── src/db/                  # Database ops
```

## 🤖 Agent Pattern
```python
class MyAgent(AutomagikAgent):
    def __init__(self):
        super().__init__(
            agent_name="my_agent",
            system_prompt=SYSTEM_PROMPT,
            tools=MyAgentTools().get_tools()
        )
    
    async def process_message(self, message: str, session_name: str = "default") -> str:
        return await self.run_agent(message, session_name)
```

## 🔧 Tech Stack
**Core**: FastAPI + Pydantic AI + PostgreSQL + uvicorn  
**LLMs**: OpenAI, Gemini, Claude, Groq, Ollama  
**Tools**: Discord, Notion, Gmail, Airtable  
**Deploy**: Docker, `bash scripts/install/setup.sh`

## 📋 Dev Commands
```bash
agent dev                    # Start with auto-reload
agent logs                   # Monitor logs
ruff check                   # Code quality
pytest                       # Run tests
```

## 🧠 Memory Templates
Use `{{variable}}` in prompts:
- `{{user_name}}` - Current user
- `{{recent_context}}` - Conversation history  
- `{{preferences}}` - User preferences
- Memory API: `/api/v1/agent/{name}/memory`

## 🎯 Priorities
**HIGH**: Use Task Master, follow patterns, maintain memory context, test thoroughly  
**MED**: Extend APIs, add tools, improve docs  
**LOW**: Infrastructure changes, base modifications

## 🚦 Quality Gates
- [ ] Task Master initialized
- [ ] Memory searched for context  
- [ ] Existing patterns reviewed
- [ ] Tests planned

**Remember**: Work systematically with Task Master. Extend framework patterns. Leverage memory context. 