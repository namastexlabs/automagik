---
description: Core agent mission, responsibilities, and critical procedures for automagik-agents framework
globs: **/*
alwaysApply: true
---
# AI Agent Mission Control

You are a **specialized coding agent** for the **Automagik Agents** project - a production-ready AI agent framework built over Pydantic AI.

## 🎯 Mission & Responsibilities

**Documentation**: [setup.md](mdc:docs/setup.md) | [running.md](mdc:docs/running.md) | [agents_overview.md](mdc:docs/agents_overview.md)

**PRIMARY OBJECTIVE**: Develop, maintain, and extend automagik-agents framework following established patterns.

**CORE RESPONSIBILITIES**:
- 🤖 **Agent Development**: Create/customize AI agents using framework patterns
- 🔧 **Tool Integration**: Develop external service integrations (Discord, Notion, Gmail, etc.)
- 🌐 **API Development**: Extend FastAPI endpoints and middleware
- 🧠 **Memory System**: Implement knowledge graph persistence and templating
- 📦 **Project Maintenance**: Setup, configuration, testing, deployment

## 🚨 Critical Procedures

### 1. **ALWAYS SEARCH MEMORY FIRST**
**Commands**: `agent-memory_search_memory_nodes|search_memory_facts` - See [04_memory_refs.md](mdc:.cursor/rules/04_memory_refs.md)
- Search for preferences, procedures, and requirements before starting
- Respect discovered knowledge in all work
- Store new discoveries immediately

### 2. **ALWAYS USE LINEAR**
**Commands**: `linear_create_issue|update_issue|list_issues|create_project` - See [01_task_system.md](mdc:.cursor/rules/01_task_system.md)

### 3. **Framework-First Development**
- **EXTEND** `AutomagikAgent`, **DON'T MODIFY** base classes
- **FOLLOW** patterns from `src/agents/simple/`
- **USE** provided tools/infrastructure vs reinventing

### 4. **Memory-Driven Development**
**Core Commands**:
```bash
# Before ANY task - search for context
agent-memory_search_memory_nodes --query "task keywords" --entity "Preference|Procedure"
agent-memory_search_memory_facts --query "relationships dependencies"

# During work - capture immediately
agent-memory_add_memory --name "Discovery" --episode_body "content" --source "text"
```

## 🛠️ Environment Setup

**Commands**: `source .venv/bin/activate && uv sync && automagik agents start`
**Details**: See [setup.md](mdc:docs/setup.md) - Use `uv` workflow, NOT pip

**Development**: `automagik agents dev` | **Quality**: `ruff check && pytest`

## 🔧 Tech Stack & Architecture

**Stack**: FastAPI + Pydantic AI + PostgreSQL + Graphiti + uvicorn  
**LLMs**: OpenAI, Gemini, Claude, Groq, Ollama  
**Memory**: Knowledge graph with preferences, procedures, facts
**Structure**: See [agents_overview.md](mdc:docs/agents_overview.md)

## 🎯 Core Development Patterns

### **Agent Extension** (MANDATORY)
```python
class MyAgent(AutomagikAgent):
    def __init__(self, config: Dict[str, str]) -> None:
        super().__init__(config)
        self._code_prompt_text = AGENT_PROMPT  # Required
        self.dependencies = AutomagikAgentsDependencies(...)
        self.tool_registry.register_default_tools(self.context)  # Required
```

### **API Endpoint Pattern**
```python
@router.post("/action", response_model=ActionResponse)
async def perform_action(
    request: ActionRequest,
    api_key: str = Depends(verify_api_key)  # Required for /api/v1/
):
    # Implementation
```

### **Memory Template Usage**
```python
SYSTEM_PROMPT = """You are an agent.
User: {{user_name}} | Context: {{recent_context}}
Preferences: {{user_preferences}}  # From memory searches
Available tools: {tools}"""
```

## 🚨 Troubleshooting Quick Fixes

**Database Connection Failed**:
```bash
sudo systemctl status postgresql  # Check PostgreSQL
echo $DATABASE_URL                # Verify environment
```

**Agent Not Loading**:
```bash
automagik agents dev              # Start with debug output
python -c "from src.agents.simple.my_agent.agent import MyAgent"  # Test import
```

**API Authentication Failing**:
```bash
curl -H "X-API-Key: your-key" http://localhost:8000/api/v1/agents  # Test auth
```

**Environment Issues**:
```bash
which python                      # Should show .venv/bin/python
pip list | grep pydantic-ai      # Verify installation
```

## 📋 Essential Commands

```bash
# Environment: source .venv/bin/activate && uv sync
# Run: automagik agents start || automagik agents dev
# Quality: ruff check && pytest tests/
# Linear: linear_create_issue --title "Issue Title" --teamId "<team-id>"
# Memory Search: agent-memory_search_memory_nodes --query "preferences" --entity "Preference"
# Memory Store: agent-memory_add_memory --name "Pattern" --episode_body "content" --source "text"
# Git: Use MCP tools - See [08_git_version_management.md](mdc:.cursor/rules/08_git_version_management.md)
```

## 🎯 Quality Gates

Before code changes: 
1. **Memory searched** for preferences/procedures
2. **Linear issue created**
3. **Patterns reviewed** from memory
4. **Tests planned**

After code changes:
1. **Patterns stored** in memory
2. **Linear updated** with progress
3. **Tests passing**

## ⚠️ Critical Rules

### ✅ ALWAYS DO
1. **Search memory first**: Check preferences/procedures before starting
2. **Activate venv**: `source .venv/bin/activate` before any Python commands
3. **Use uv workflow**: `uv sync|add|remove` (NOT pip)
4. **Extend AutomagikAgent**: Never modify base classes
5. **Use Linear**: For all development work
6. **Record in memory**: Successful patterns and solutions immediately

### ❌ NEVER DO
1. **Skip memory search**: Missing established patterns/preferences
2. **Skip venv activation**: Causes import/dependency issues
3. **Use pip commands**: Use uv workflow
4. **Modify base classes**: Extend, don't modify
5. **Bypass authentication**: All `/api/v1/` endpoints require API keys
6. **Work without Linear**: Lose development progress

---

**Remember**: You are an extension of the automagik-agents framework. Always search memory first, respect discovered knowledge, follow patterns, use Linear.
