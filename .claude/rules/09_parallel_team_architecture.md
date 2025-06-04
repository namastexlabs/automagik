---
description: Revolutionary parallel team architecture enabling 5-agent simultaneous development with MCP communication
globs: **/*
alwaysApply: true
---

# Parallel Team Architecture - Revolutionary Development

## 🚀 **Mission: 5x Development Speed**

**Transform from single-agent serial development to 5-agent parallel development**

**Target**: **5x speed improvement** through true parallel development with **zero conflicts**

## 🎯 **Team Structure**

### **Alpha Agent - Orchestrator** (main branch)
- **Role**: Epic coordination, task distribution, integration oversight
- **Branch**: `main` (coordination hub)
- **MCP Port**: `3001`
- **Focus**: Epic breakdown, team coordination, final integration
- **Memory Prefix**: `[P-EPIC]`

### **Beta Agent - Core Builder** (feature-core worktree)
- **Role**: Core framework, agents, memory system
- **Worktree**: `../am-agents-core` → `feature-core` branch
- **MCP Port**: `3002`
- **Focus**: `src/agents/`, `src/memory/`, core infrastructure
- **Memory Prefix**: `[P-CORE]`

### **Delta Agent - API Builder** (feature-api worktree)
- **Role**: FastAPI endpoints, authentication, middleware
- **Worktree**: `../am-agents-api` → `feature-api` branch
- **MCP Port**: `3003`
- **Focus**: `src/api/`, authentication, routing
- **Memory Prefix**: `[P-API]`

### **Epsilon Agent - Tool Builder** (feature-tools worktree)
- **Role**: External integrations, tool development
- **Worktree**: `../am-agents-tools` → `feature-tools` branch
- **MCP Port**: `3004`
- **Focus**: `src/tools/`, external service integrations
- **Memory Prefix**: `[P-TOOLS]`

### **Gamma Agent - Quality Engineer** (feature-tests worktree)
- **Role**: Testing, quality assurance, documentation
- **Worktree**: `../am-agents-tests` → `feature-tests` branch
- **MCP Port**: `3005`
- **Focus**: `tests/`, documentation, quality gates
- **Memory Prefix**: `[P-TESTS]`

## 🏗️ **Worktree Management**

### **Setup Parallel Worktrees**
```bash
# Alpha Agent (Orchestrator) - stays on main
cd /root/workspace/am-agents-labs

# Beta Agent (Core Builder)
git worktree add ../am-agents-core feature-core
git worktree add ../am-agents-api feature-api
git worktree add ../am-agents-tools feature-tools
git worktree add ../am-agents-tests feature-tests

# Verify worktree structure
git worktree list
```

### **Worktree Structure**
```
/root/workspace/
├── am-agents-labs/          # Alpha Agent (main branch)
├── am-agents-core/          # Beta Agent (feature-core branch)
├── am-agents-api/           # Delta Agent (feature-api branch)
├── am-agents-tools/         # Epsilon Agent (feature-tools branch)
└── am-agents-tests/         # Gamma Agent (feature-tests branch)
```

### **Component Isolation**
- **No file conflicts**: Each agent works in separate worktree
- **Independent development**: Parallel commits without interference
- **Selective integration**: Merge components when ready

## 🔗 **MCP Communication Protocol**

### **MCP Server Configuration**
```json
// .mcp.json for each agent
{
  "mcpServers": {
    "alpha-orchestrator": {
      "command": "python",
      "args": ["-m", "mcp.server.alpha"],
      "env": {"MCP_PORT": "3001"}
    },
    "beta-core": {
      "command": "python", 
      "args": ["-m", "mcp.server.beta"],
      "env": {"MCP_PORT": "3002"}
    },
    "delta-api": {
      "command": "python",
      "args": ["-m", "mcp.server.delta"], 
      "env": {"MCP_PORT": "3003"}
    },
    "epsilon-tools": {
      "command": "python",
      "args": ["-m", "mcp.server.epsilon"],
      "env": {"MCP_PORT": "3004"}
    },
    "gamma-tests": {
      "command": "python",
      "args": ["-m", "mcp.server.gamma"],
      "env": {"MCP_PORT": "3005"}
    }
  }
}
```

### **Inter-Agent Communication**
```python
# Agent communication via MCP
async def coordinate_with_team(agent_id: str, message: dict):
    """Send coordination message to specific agent"""
    mcp_client = MCPClient(f"localhost:{MCP_PORTS[agent_id]}")
    return await mcp_client.send_message(message)

# Example: Alpha coordinating with Beta
await coordinate_with_team("beta-core", {
    "type": "task_assignment",
    "epic": "NMSTX-123",
    "component": "agent_memory_integration",
    "priority": "high"
})
```

## 🧠 **Memory Coordination Framework**

### **Component-Specific Memory Patterns**
```bash
# Alpha Agent - Epic coordination
agent-memory_add_memory \
  --name "[P-EPIC] Epic Breakdown Pattern" \
  --episode_body "Epic NMSTX-123 broken into 5 component tasks" \
  --source "text"

# Beta Agent - Core patterns
agent-memory_add_memory \
  --name "[P-CORE] Agent Extension Pattern" \
  --episode_body "AutomagikAgent extension with tool registry" \
  --source "text"

# Delta Agent - API patterns  
agent-memory_add_memory \
  --name "[P-API] Endpoint Authentication Pattern" \
  --episode_body "FastAPI endpoint with API key validation" \
  --source "text"

# Epsilon Agent - Tool patterns
agent-memory_add_memory \
  --name "[P-TOOLS] Discord Integration Pattern" \
  --episode_body "Discord tool with async message handling" \
  --source "text"

# Gamma Agent - Test patterns
agent-memory_add_memory \
  --name "[P-TESTS] Integration Test Pattern" \
  --episode_body "Agent integration test with mock dependencies" \
  --source "text"
```

### **Cross-Component Coordination**
```bash
# Search for cross-component dependencies
agent-memory_search_memory_facts --query "depends on requires interface"

# Store interface contracts
agent-memory_add_memory \
  --name "[P-INTERFACE] Core-API Contract" \
  --episode_body "{\"endpoint\": \"/api/v1/agents\", \"requires\": \"AutomagikAgent\", \"provides\": \"AgentResponse\"}" \
  --source "json"
```

## 🔄 **Parallel Workflow Orchestration**

### **Epic Breakdown Process**
```python
# Alpha Agent workflow
async def orchestrate_epic(epic_id: str):
    """Break epic into component tasks and coordinate team"""
    
    # 1. Analyze epic requirements
    epic_analysis = await analyze_epic_requirements(epic_id)
    
    # 2. Create component tasks
    component_tasks = {
        "core": await create_core_tasks(epic_analysis),
        "api": await create_api_tasks(epic_analysis),
        "tools": await create_tool_tasks(epic_analysis),
        "tests": await create_test_tasks(epic_analysis)
    }
    
    # 3. Assign to agents via MCP
    for component, tasks in component_tasks.items():
        await coordinate_with_team(f"{component}-agent", {
            "type": "task_assignment",
            "epic": epic_id,
            "tasks": tasks
        })
    
    # 4. Monitor progress
    await monitor_epic_progress(epic_id)
```

### **Component Development Workflow**
```python
# Beta Agent (Core) workflow
async def develop_core_component(task_assignment: dict):
    """Develop core component in isolation"""
    
    # 1. Switch to component worktree
    await switch_worktree("../am-agents-core")
    
    # 2. Implement component
    await implement_core_feature(task_assignment)
    
    # 3. Store patterns in memory
    await store_core_patterns(task_assignment)
    
    # 4. Signal completion to Alpha
    await coordinate_with_team("alpha-orchestrator", {
        "type": "component_complete",
        "component": "core",
        "task": task_assignment["task_id"]
    })
```

## 🔧 **Interface Coordination**

### **Component Interface Contracts**
```python
# Store interface definitions in memory
INTERFACE_CONTRACTS = {
    "core_to_api": {
        "provides": ["AutomagikAgent", "AgentConfig"],
        "requires": ["FastAPI", "APIResponse"]
    },
    "api_to_tools": {
        "provides": ["ToolRegistry", "ToolContext"],
        "requires": ["ExternalTool", "ToolResponse"]
    },
    "tools_to_tests": {
        "provides": ["MockTool", "TestFixture"],
        "requires": ["TestCase", "Assertion"]
    }
}
```

### **Interface Validation**
```bash
# Validate interfaces before integration
agent-memory_search_memory_facts --query "interface contract provides requires"

# Store interface changes
agent-memory_add_memory \
  --name "[P-INTERFACE] API Contract Change" \
  --episode_body "Updated AgentResponse to include status field" \
  --source "text"
```

## 🚀 **Team Startup Protocol**

### **Parallel Team Initialization**
```bash
#!/bin/bash
# scripts/start_parallel_team.sh

# 1. Setup worktrees
echo "Setting up parallel worktrees..."
git worktree add ../am-agents-core feature-core
git worktree add ../am-agents-api feature-api  
git worktree add ../am-agents-tools feature-tools
git worktree add ../am-agents-tests feature-tests

# 2. Start MCP servers for each agent
echo "Starting MCP servers..."
python -m mcp.server.alpha --port 3001 &
python -m mcp.server.beta --port 3002 &
python -m mcp.server.delta --port 3003 &
python -m mcp.server.epsilon --port 3004 &
python -m mcp.server.gamma --port 3005 &

# 3. Initialize memory coordination
echo "Initializing team memory..."
agent-memory_add_memory \
  --name "[P-TEAM] Parallel Team Startup" \
  --episode_body "5-agent parallel team initialized with MCP communication" \
  --source "text"

echo "Parallel team ready for 5x development speed!"
```

### **Agent Specialization Prompts**
```python
# Alpha Agent (Orchestrator) system prompt
ALPHA_PROMPT = """You are Alpha, the Orchestrator of a 5-agent parallel development team.

MISSION: Coordinate epic breakdown and team integration for 5x development speed.

TEAM STRUCTURE:
- Beta (Core Builder): Agents, memory, core infrastructure
- Delta (API Builder): FastAPI, authentication, routing  
- Epsilon (Tool Builder): External integrations, tools
- Gamma (Quality Engineer): Testing, documentation, quality

COORDINATION PROTOCOL:
1. Break epics into component tasks
2. Assign via MCP communication
3. Monitor progress through memory
4. Orchestrate integration
5. Ensure quality gates

MEMORY PREFIX: [P-EPIC]
MCP PORT: 3001
WORKTREE: main (coordination hub)

Available tools: {tools}
Team status: {{team_status}}
Current epic: {{current_epic}}
"""

# Beta Agent (Core Builder) system prompt  
BETA_PROMPT = """You are Beta, the Core Builder of a 5-agent parallel development team.

MISSION: Build core framework, agents, and memory systems in isolation.

SPECIALIZATION:
- AutomagikAgent extensions
- Memory system integration
- Core infrastructure
- Agent patterns

COORDINATION:
- Receive tasks from Alpha via MCP
- Develop in feature-core worktree
- Store patterns with [P-CORE] prefix
- Signal completion to team

MEMORY PREFIX: [P-CORE]
MCP PORT: 3002
WORKTREE: ../am-agents-core (feature-core branch)

Available tools: {tools}
Current tasks: {{core_tasks}}
Interface contracts: {{core_interfaces}}
"""
```

## 📊 **Quality Gates & Integration**

### **Component Quality Gates**
```python
# Quality gates for each component
QUALITY_GATES = {
    "core": [
        "All AutomagikAgent extensions follow pattern",
        "Memory integration tests pass",
        "Core patterns stored in memory"
    ],
    "api": [
        "All endpoints have authentication",
        "API documentation updated",
        "Response models validated"
    ],
    "tools": [
        "External integrations tested",
        "Tool registry updated",
        "Error handling implemented"
    ],
    "tests": [
        "Integration tests cover all components",
        "Quality metrics meet thresholds",
        "Documentation updated"
    ]
}
```

### **Progressive Integration Strategy**
```bash
# Integration workflow
# 1. Component completion signals
agent-memory_search_memory_nodes --query "[P-CORE] component complete" --entity "Procedure"

# 2. Interface validation
agent-memory_search_memory_facts --query "interface contract validated"

# 3. Progressive merge to main
git checkout main
git merge feature-core    # Beta's work
git merge feature-api     # Delta's work  
git merge feature-tools   # Epsilon's work
git merge feature-tests   # Gamma's work

# 4. Final integration testing
pytest tests/integration/parallel_team/
```

## 🎯 **Success Metrics**

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

### **Memory Pattern Metrics**
```bash
# Track team success patterns
agent-memory_search_memory_nodes --query "[P-TEAM] success pattern" --entity "Procedure"

# Monitor component specialization
agent-memory_search_memory_nodes --query "[P-CORE] [P-API] [P-TOOLS] [P-TESTS]" --max_nodes 50
```

## 🚨 **Conflict Resolution**

### **Worktree Conflict Prevention**
- **File isolation**: Each agent works in separate worktree
- **Component boundaries**: Clear ownership of directories
- **Interface contracts**: Defined communication protocols
- **Memory coordination**: Shared understanding through memory

### **Integration Conflict Resolution**
```bash
# If conflicts occur during integration
git checkout main
git merge --no-ff feature-core
# Resolve conflicts based on component specialization
# Core conflicts: Beta agent expertise
# API conflicts: Delta agent expertise
# Tool conflicts: Epsilon agent expertise
# Test conflicts: Gamma agent expertise
```

---

**Remember**: This parallel architecture enables true simultaneous development across all components. Each agent specializes in their domain, communicates via MCP, and coordinates through memory. The result is 5x development speed with zero conflicts through worktree isolation and expert specialization. 