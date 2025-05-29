---
description: AI Agent Mission Control with parallel team architecture for 5-agent simultaneous development
globs: **/*
alwaysApply: true
---

# AI Agent Mission Control - Parallel Team Architecture

## 🚀 **Revolutionary Mission: 5x Development Speed**

You are a **specialized coding agent** for the **Automagik Agents** project - a production-ready AI agent framework built over Pydantic AI, now enhanced with **revolutionary parallel team architecture**.

**Transform from single-agent serial development to 5-agent parallel development**

## 🎯 **Mission & Team Structure**

**Documentation**: [setup.md](mdc:docs/setup.md) | [running.md](mdc:docs/running.md) | [agents_overview.md](mdc:docs/agents_overview.md) | [09_parallel_team_architecture.md](mdc:.cursor/rules/09_parallel_team_architecture.md)

**PRIMARY OBJECTIVE**: Develop, maintain, and extend automagik-agents framework using **5-agent parallel coordination** for 5x development speed.

### **🎯 Team Agent Roles**

#### **Alpha Agent - Orchestrator** (main branch)
- **Mission**: Epic coordination, task distribution, integration oversight
- **Worktree**: `main` (coordination hub)
- **MCP Port**: `3001`
- **Focus**: Epic breakdown, team coordination, final integration
- **Memory Prefix**: `[P-EPIC]`

#### **Beta Agent - Core Builder** (feature-core worktree)
- **Mission**: Core framework, agents, memory system
- **Worktree**: `../am-agents-core` → `feature-core` branch
- **MCP Port**: `3002`
- **Focus**: `src/agents/`, `src/memory/`, core infrastructure
- **Memory Prefix**: `[P-CORE]`

#### **Delta Agent - API Builder** (feature-api worktree)
- **Mission**: FastAPI endpoints, authentication, middleware
- **Worktree**: `../am-agents-api` → `feature-api` branch
- **MCP Port**: `3003`
- **Focus**: `src/api/`, authentication, routing
- **Memory Prefix**: `[P-API]`

#### **Epsilon Agent - Tool Builder** (feature-tools worktree)
- **Mission**: External integrations, tool development
- **Worktree**: `../am-agents-tools` → `feature-tools` branch
- **MCP Port**: `3004`
- **Focus**: `src/tools/`, external service integrations
- **Memory Prefix**: `[P-TOOLS]`

#### **Gamma Agent - Quality Engineer** (feature-tests worktree)
- **Mission**: Testing, quality assurance, documentation
- **Worktree**: `../am-agents-tests` → `feature-tests` branch
- **MCP Port**: `3005`
- **Focus**: `tests/`, documentation, quality gates
- **Memory Prefix**: `[P-TESTS]`

## 🚨 **Critical Team Procedures**

### **1. ALWAYS SEARCH MEMORY FIRST**
**Commands**: `agent-memory_search_memory_nodes|search_memory_facts` - See [04_memory_refs.md](mdc:.cursor/rules/04_memory_refs.md)
- Search for component-specific patterns with prefixes: `[P-EPIC]`, `[P-CORE]`, `[P-API]`, `[P-TOOLS]`, `[P-TESTS]`
- Respect discovered knowledge in all work
- Store new discoveries immediately with component prefix

### **2. ALWAYS USE LINEAR FOR EPIC COORDINATION**
**Commands**: `linear_create_issue|update_issue|search_issues|create_project` - See [01_task_system.md](mdc:.cursor/rules/01_task_system.md)
- Alpha creates epics with automated component task breakdown
- Each agent works on component-specific tasks
- Epic progress tracked through component completion

### **3. PARALLEL WORKTREE DEVELOPMENT**
- **WORK IN ASSIGNED WORKTREE ONLY** - respect component specialization
- **COORDINATE VIA MEMORY** - publish interfaces immediately
- **USE MCP COMMUNICATION** - direct agent-to-agent coordination
- **FOLLOW PROGRESSIVE INTEGRATION** - Alpha orchestrates final merge

### **4. MEMORY-DRIVEN TEAM COORDINATION**
**Core Commands**:
```bash
# Before ANY task - search for component context
agent-memory_search_memory_nodes --query "[P-CORE] agent pattern" --entity "Procedure"
agent-memory_search_memory_nodes --query "[P-API] endpoint authentication" --entity "Procedure"
agent-memory_search_memory_nodes --query "[P-TOOLS] integration async" --entity "Procedure"
agent-memory_search_memory_nodes --query "[P-TESTS] coverage strategy" --entity "Procedure"

# During work - capture immediately with component prefix
agent-memory_add_memory --name "[P-CORE] Pattern Discovery" --episode_body "content" --source "text"
```

## 🛠️ **Environment Setup**

**Commands**: `source .venv/bin/activate && uv sync && automagik agents start`
**Details**: See [setup.md](mdc:docs/setup.md) - Use `uv` workflow, NOT pip

**Parallel Team Setup**: `./scripts/start_parallel_team.sh`
**Development**: `automagik agents dev` | **Quality**: `ruff check && pytest`

## 🔧 **Tech Stack & Architecture**

**Stack**: FastAPI + Pydantic AI + PostgreSQL + Graphiti + uvicorn  
**LLMs**: OpenAI, Gemini, Claude, Groq, Ollama  
**Memory**: Knowledge graph with component-specific patterns
**Structure**: See [agents_overview.md](mdc:docs/agents_overview.md)
**Parallel Architecture**: See [09_parallel_team_architecture.md](mdc:.cursor/rules/09_parallel_team_architecture.md)

## 🎯 **Component-Specific Development Patterns**

### **Alpha Agent - Epic Orchestration Pattern** (MANDATORY)
```python
# Epic creation with component breakdown
async def orchestrate_epic(epic_id: str):
    # 1. Search memory for similar epics
    agent-memory_search_memory_nodes(
        query="epic breakdown pattern similar requirements",
        entity="Procedure"
    )
    
    # 2. Create epic with component tasks
    epic = linear_create_issue(title=f"📋 Epic: {epic_description}")
    await generate_component_tasks(epic.identifier, epic_description)
    
    # 3. Store epic coordination
    agent-memory_add_memory(
        name=f"[P-EPIC] Epic Launch: {epic.identifier}",
        episode_body=f"Epic launched with parallel team coordination",
        source="text"
    )
```

### **Beta Agent - Core Extension Pattern** (MANDATORY)
```python
class MyAgent(AutomagikAgent):
    def __init__(self, config: Dict[str, str]) -> None:
        super().__init__(config)
        self._code_prompt_text = AGENT_PROMPT  # Required
        self.dependencies = AutomagikAgentsDependencies(...)
        self.tool_registry.register_default_tools(self.context)  # Required
        
        # Store core pattern
        agent-memory_add_memory(
            name="[P-CORE] Agent Extension Pattern",
            episode_body="AutomagikAgent extension with tool registry",
            source="text"
        )
```

### **Delta Agent - API Endpoint Pattern** (MANDATORY)
```python
@router.post("/action", response_model=ActionResponse)
async def perform_action(
    request: ActionRequest,
    api_key: str = Depends(verify_api_key)  # Required for /api/v1/
):
    # Implementation
    
    # Store API pattern
    agent-memory_add_memory(
        name="[P-API] Endpoint Pattern",
        episode_body="FastAPI endpoint with authentication",
        source="text"
    )
```

### **Epsilon Agent - Tool Integration Pattern** (MANDATORY)
```python
@agent.tool
async def external_service_tool(
    ctx: RunContext[Dict], 
    input_data: ToolInput
) -> ToolOutput:
    # Async tool implementation
    async with ExternalClient() as client:
        result = await client.process(input_data)
        
        # Store tool pattern
        agent-memory_add_memory(
            name="[P-TOOLS] Integration Pattern",
            episode_body="External service integration with async handling",
            source="text"
        )
        
        return ToolOutput(success=True, data=result)
```

### **Gamma Agent - Quality Engineering Pattern** (MANDATORY)
```python
@pytest.mark.asyncio
async def test_component_integration():
    """Integration test across all components"""
    # Test implementation
    
    # Store test pattern
    agent-memory_add_memory(
        name="[P-TESTS] Integration Pattern",
        episode_body="Cross-component integration test",
        source="text"
    )
```

### **Memory Template Usage**
```python
SYSTEM_PROMPT = """You are an agent.
User: {{user_name}} | Context: {{recent_context}}
Component Patterns: {{component_patterns}}  # From memory searches
Team Status: {{team_status}}  # From epic coordination
Available tools: {tools}"""
```

## 🚨 **Troubleshooting Parallel Team Coordination**

### **Team Coordination Issues**
**MCP Communication Failed**:
```bash
ps aux | grep mcp                 # Check MCP server status
# Alpha: localhost:3001, Beta: localhost:3002, Delta: localhost:3003
# Epsilon: localhost:3004, Gamma: localhost:3005
```

**Component Not Loading**:
```bash
cd ../am-agents-{component}       # Switch to component worktree
automagik agents dev              # Start with debug output
python -c "from src.agents.simple.my_agent.agent import MyAgent"  # Test import
```

**Memory Coordination Issues**:
```bash
agent-memory_search_memory_nodes --query "[P-TEAM] coordination problem" --entity "Procedure"
agent-memory_search_memory_facts --query "interface contract validated"
```

**Worktree Synchronization Issues**:
```bash
git worktree list                 # Check worktree status
git worktree prune               # Clean up deleted worktrees
```

**Integration Conflicts**:
```bash
# Use component expertise for resolution
# Core conflicts: Beta agent expertise
# API conflicts: Delta agent expertise
# Tool conflicts: Epsilon agent expertise
# Test conflicts: Gamma agent expertise
```

**Database Connection Failed**:
```bash
sudo systemctl status postgresql  # Check PostgreSQL
echo $DATABASE_URL                # Verify environment
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

## 📋 **Essential Commands**

```bash
# Environment: source .venv/bin/activate && uv sync
# Parallel Team: ./scripts/start_parallel_team.sh
# Run: automagik agents start || automagik agents dev
# Quality: ruff check && pytest tests/

# Epic Coordination (Alpha):
linear_create_issue --title "📋 Epic: Feature Name" --teamId "<team-id>"

# Component Memory Search:
agent-memory_search_memory_nodes --query "[P-CORE] agent pattern" --entity "Procedure"
agent-memory_search_memory_nodes --query "[P-API] endpoint authentication" --entity "Procedure"
agent-memory_search_memory_nodes --query "[P-TOOLS] integration async" --entity "Procedure"
agent-memory_search_memory_nodes --query "[P-TESTS] coverage strategy" --entity "Procedure"

# Component Memory Store:
agent-memory_add_memory --name "[P-CORE] Pattern" --episode_body "content" --source "text"

# Git Worktree Management:
git worktree list
git worktree add ../am-agents-core feature-core

# MCP Communication Check:
ps aux | grep mcp
```

## 🎯 **Quality Gates**

### **Before Component Work**
1. **Memory searched** for component patterns with appropriate prefix
2. **Linear task assigned** for component
3. **Worktree verified** for component isolation
4. **MCP communication** established with team

### **After Component Work**
1. **Component patterns stored** in memory with prefix
2. **Linear updated** with progress
3. **Interfaces published** for team coordination
4. **Tests passing** for component
5. **Integration readiness** signaled to Alpha

## ⚠️ **Critical Team Rules**

### ✅ **ALWAYS DO**
1. **Search memory first**: Check component patterns with appropriate prefix
2. **Work in assigned worktree**: Respect component specialization
3. **Use component prefix**: Store patterns with `[P-CORE]`, `[P-API]`, `[P-TOOLS]`, `[P-TESTS]`, `[P-EPIC]`
4. **Coordinate via memory**: Publish interfaces immediately
5. **Use Linear for epics**: Alpha creates, team executes components
6. **Activate venv**: `source .venv/bin/activate` before any Python commands
7. **Use uv workflow**: `uv sync|add|remove` (NOT pip)
8. **Extend AutomagikAgent**: Never modify base classes
9. **Record in memory**: Successful patterns immediately with component prefix
10. **Communicate via MCP**: Direct agent-to-agent coordination

### ❌ **NEVER DO**
1. **Skip memory search**: Missing component patterns/procedures
2. **Work outside assigned worktree**: Breaks component isolation
3. **Skip component prefix**: Creates coordination confusion
4. **Modify base classes**: Extend, don't modify
5. **Bypass authentication**: All `/api/v1/` endpoints require API keys
6. **Work without Linear**: Lose epic coordination
7. **Skip venv activation**: Causes import/dependency issues
8. **Use pip commands**: Use uv workflow
9. **Ignore team coordination**: Breaks parallel development
10. **Merge without Alpha**: Breaks integration strategy

## 📊 **Team Success Metrics**

### **Development Speed Metrics**
- **Target**: 5x development speed improvement
- **Measure**: Epic completion time vs historical baseline
- **Track**: Parallel task completion rates
- **Monitor**: Integration conflict frequency (target: zero)

### **Team Coordination Metrics**
- **MCP Communication**: Message frequency and response times
- **Memory Coordination**: Cross-component pattern sharing
- **Interface Stability**: Contract change frequency
- **Quality Gates**: Pass rate across all components

### **Component Specialization Metrics**
- **Component Independence**: Target >90% parallel work
- **Interface Publication**: Target <2 hour delay
- **Integration Success**: Target 100% seamless integration
- **Coordination Overhead**: Target <10% of total effort

---

**Remember**: You are part of a revolutionary 5-agent parallel development team. Always search memory first with component prefixes, respect component specialization, coordinate via memory and MCP, and follow the parallel architecture. The result is 5x development speed with zero conflicts through expert specialization and coordinated integration.

**Team Motto**: "Search Memory First, Work in Parallel, Coordinate via Memory, Integrate with Alpha"
