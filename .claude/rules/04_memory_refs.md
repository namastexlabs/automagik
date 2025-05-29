---
description: Enhanced memory API commands, team coordination patterns, and component-specific templates for automagik-agents parallel architecture
globs: **/*
alwaysApply: true
---

# Enhanced Memory References - Parallel Team Coordination

## 🎯 Memory Framework Overview

**ENHANCED FOR PARALLEL TEAMS**: Memory-driven coordination system supporting 5 specialized agents working in parallel worktrees with component-specific patterns.

**Documentation**: [09_parallel_team_architecture.md](mdc:.cursor/rules/09_parallel_team_architecture.md) | [03_dev_workflow.md](mdc:.cursor/rules/03_dev_workflow.md)

## 🧠 Core Memory Operations

### **Essential Memory Commands**
```bash
# Search for patterns and procedures
agent-memory_search_memory_nodes --query "search terms" --entity "Preference|Procedure"
agent-memory_search_memory_facts --query "relationships dependencies"

# Store discoveries and patterns
agent-memory_add_memory --name "Title" --episode_body "content" --source "text|json|message"
```

## 👥 **Component-Specific Memory Patterns**

### **Team Coordination Prefixes**

**Epic-Level Coordination (Alpha)**:
```bash
[P-EPIC]     # Epic progress and coordination
[T-ASSIGN]   # Task assignments to team members
[T-BLOCKED]  # Team blocking dependencies
[T-COMPLETE] # Component completion notifications
```

**Core Development (Beta)**:
```bash
[P-CORE]     # Core implementation progress
[I-INTERFACE] # Published agent interfaces
[A-PATTERN]  # Agent development patterns
[A-COMPLETE] # Agent completion status
```

**API Development (Delta)**:
```bash
[P-API]      # API implementation progress
[I-CONTRACT] # API contracts and schemas
[E-ENDPOINT] # Endpoint definitions
[D-DOC]      # API documentation
```

**Tool Development (Epsilon)**:
```bash
[P-TOOL]     # Tool implementation progress
[T-SCHEMA]   # Tool input/output schemas
[T-INTEGRATION] # External service integrations
[T-ASYNC]    # Async operation patterns
```

**Quality Engineering (Gamma)**:
```bash
[Q-PLAN]     # Quality and testing strategy
[Q-COVERAGE] # Test coverage metrics
[Q-INTEGRATION] # Integration test results
[Q-QUALITY]  # Quality gate results
```

**Cross-Component Coordination**:
```bash
[I-DEPENDENCY] # Dependencies between components
[I-READY]    # Component readiness notifications
[C-SYNC]     # Component synchronization points
[M-MILESTONE] # Major milestone completions
```

## 🚀 **Team Memory Workflows**

### **1. Epic Launch (Alpha Orchestration)**
```bash
# Alpha searches for epic breakdown patterns
agent-memory_search_memory_nodes --query "epic breakdown discord integration" --entity "Procedure"
agent-memory_search_memory_facts --query "component dependencies architecture"

# Alpha creates epic coordination entry
agent-memory_add_memory \
  --name "Epic Launch: Discord Integration" \
  --episode_body "[P-EPIC] Epic: Discord Agent | Components: Core(Beta), API(Delta), Tools(Epsilon), Tests(Gamma) | Deadline: 2025-01-30 | Status: Initialized" \
  --source "text"

# Alpha assigns component tasks
agent-memory_add_memory \
  --name "Task Assignment: Discord Epic" \
  --episode_body "[T-ASSIGN] Beta: Discord agent class, message handling | Delta: /discord endpoints, webhook routes | Epsilon: Discord API integration, real-time events | Gamma: Integration test suite, discord mock framework" \
  --source "text"
```

### **2. Core Development (Beta Workflow)**
```bash
# Beta discovers assigned tasks
agent-memory_search_memory_nodes --query "task assignment core implementation discord" --entity "Procedure"

# Beta implements and publishes interfaces
agent-memory_add_memory \
  --name "Core Progress: Discord Agent" \
  --episode_body "[P-CORE] Discord Agent: 70% complete | Classes: DiscordAgent, MessageHandler | Status: Ready for API integration" \
  --source "text"

# Beta publishes interfaces for team
agent-memory_add_memory \
  --name "Core Interfaces: Discord Agent" \
  --episode_body "[I-INTERFACE] {\\\"agent_class\\\": \\\"DiscordAgent\\\", \\\"methods\\\": [\\\"send_message\\\", \\\"get_channels\\\", \\\"listen_events\\\"], \\\"schemas\\\": {\\\"message\\\": \\\"MessageSchema\\\", \\\"channel\\\": \\\"ChannelSchema\\\"}}" \
  --source "json"

# Beta reports completion
agent-memory_add_memory \
  --name "Core Component Ready" \
  --episode_body "[A-COMPLETE] Discord Agent core implementation complete | Interfaces published | Ready for integration" \
  --source "text"
```

### **3. API Development (Delta Workflow)**
```bash
# Delta coordinates with core
agent-memory_search_memory_nodes --query "core interfaces discord agent published" --entity "Procedure"

# Delta implements API endpoints
agent-memory_add_memory \
  --name "API Progress: Discord Endpoints" \
  --episode_body "[P-API] Discord API: 60% complete | Endpoints: /discord/send, /discord/channels | Auth: Integrated | Status: Active development" \
  --source "text"

# Delta publishes API contracts
agent-memory_add_memory \
  --name "API Contracts: Discord" \
  --episode_body "[I-CONTRACT] {\\\"endpoints\\\": [{\\\"/discord/send\\\": {\\\"method\\\": \\\"POST\\\", \\\"auth\\\": \\\"required\\\", \\\"schema\\\": \\\"MessageRequest\\\"}}], \\\"models\\\": [\\\"MessageRequest\\\", \\\"ChannelResponse\\\"]}" \
  --source "json"
```

### **4. Tool Development (Epsilon Workflow)**
```bash
# Epsilon discovers tool requirements
agent-memory_search_memory_nodes --query "tool requirements discord integration external" --entity "Procedure"

# Epsilon implements Discord tools
agent-memory_add_memory \
  --name "Tool Progress: Discord Integration" \
  --episode_body "[P-TOOL] Discord Tools: 80% complete | Tools: discord_send, discord_listen | Async: Implemented | Rate limiting: Active" \
  --source "text"

# Epsilon publishes tool schemas
agent-memory_add_memory \
  --name "Tool Schemas: Discord" \
  --episode_body "[T-SCHEMA] {\\\"discord_send\\\": {\\\"input\\\": \\\"MessageInput\\\", \\\"output\\\": \\\"MessageOutput\\\"}, \\\"discord_listen\\\": {\\\"input\\\": \\\"ListenInput\\\", \\\"output\\\": \\\"EventOutput\\\"}}" \
  --source "json"
```

### **5. Quality Engineering (Gamma Workflow)**
```bash
# Gamma develops test strategy
agent-memory_search_memory_nodes --query "testing strategy integration patterns" --entity "Procedure"

# Gamma creates quality plan
agent-memory_add_memory \
  --name "Test Strategy: Discord Integration" \
  --episode_body "[Q-PLAN] {\\\"strategy\\\": \\\"integration_first\\\", \\\"coverage_target\\\": 95, \\\"test_types\\\": [\\\"unit\\\", \\\"integration\\\", \\\"e2e\\\"], \\\"mock_framework\\\": \\\"discord_mock\\\"}" \
  --source "json"

# Gamma reports quality results
agent-memory_add_memory \
  --name "Quality Assessment: Discord Epic" \
  --episode_body "[Q-COVERAGE] Coverage: 94% | Integration tests: 25/25 passing | E2E tests: 8/8 passing | Status: Quality gates met" \
  --source "text"
```

## 🔄 **Cross-Component Coordination**

### **Interface Discovery Patterns**
```bash
# Any agent can discover available interfaces
agent-memory_search_memory_nodes --query "interfaces published core api tool" --entity "Procedure"

# Search for specific component readiness
agent-memory_search_memory_nodes --query "core component ready discord" --entity "Procedure"
agent-memory_search_memory_nodes --query "api contracts published" --entity "Procedure"
agent-memory_search_memory_nodes --query "tool schemas published" --entity "Procedure"
```

### **Dependency Coordination**
```bash
# Track component dependencies
agent-memory_add_memory \
  --name "Component Dependencies: Discord Epic" \
  --episode_body "[I-DEPENDENCY] {\\\"core_ready\\\": true, \\\"api_needs\\\": [\\\"core_interfaces\\\"], \\\"tools_needs\\\": [\\\"core_interfaces\\\"], \\\"tests_needs\\\": [\\\"all_components\\\"]}" \
  --source "json"

# Mark component readiness
agent-memory_add_memory \
  --name "Component Readiness Update" \
  --episode_body "[I-READY] Core: ✅ Ready | API: 🟡 In Progress | Tools: 🟡 In Progress | Tests: 🔵 Waiting" \
  --source "text"
```

### **Milestone Coordination**
```bash
# Alpha tracks team milestones
agent-memory_add_memory \
  --name "Team Milestone: 50% Complete" \
  --episode_body "[M-MILESTONE] Discord Epic 50% complete | Core: 100% | API: 75% | Tools: 60% | Tests: 25% | Blockers: None | ETA: 2 days" \
  --source "text"
```

## 📊 **Memory Template Variables**

### **Agent Prompt Templates with Team Context**

**Alpha (Orchestrator) Template**:
```python
ALPHA_SYSTEM_PROMPT = """You are Alpha, the Epic Orchestrator.

**Current Epic**: {{epic_name}}
**Team Status**: {{team_progress}}
**Components**: {{component_status}}
**Blockers**: {{team_blockers}}
**Next Actions**: {{coordination_actions}}

Your role: Coordinate team, resolve blockers, ensure delivery.
Team: {{team_assignments}}"""
```

**Beta (Core) Template**:
```python
BETA_SYSTEM_PROMPT = """You are Beta, the Core Builder.

**Assignment**: {{core_assignment}}
**Progress**: {{core_progress}}
**Interfaces**: {{published_interfaces}}
**Dependencies**: {{core_dependencies}}
**Team Coordination**: {{team_status}}

Your role: Build core agent logic, publish interfaces.
Focus: {{current_focus}}"""
```

**Delta (API) Template**:
```python
DELTA_SYSTEM_PROMPT = """You are Delta, the API Builder.

**Assignment**: {{api_assignment}}
**Progress**: {{api_progress}}
**Core Interfaces**: {{available_interfaces}}
**Endpoints**: {{implemented_endpoints}}
**Team Coordination**: {{team_status}}

Your role: Build FastAPI endpoints, create documentation.
Focus: {{current_focus}}"""
```

**Epsilon (Tools) Template**:
```python
EPSILON_SYSTEM_PROMPT = """You are Epsilon, the Tool Builder.

**Assignment**: {{tool_assignment}}
**Progress**: {{tool_progress}}
**Integrations**: {{external_services}}
**Schemas**: {{tool_schemas}}
**Team Coordination**: {{team_status}}

Your role: Build external integrations, define tool schemas.
Focus: {{current_focus}}"""
```

**Gamma (Quality) Template**:
```python
GAMMA_SYSTEM_PROMPT = """You are Gamma, the Quality Engineer.

**Assignment**: {{quality_assignment}}
**Strategy**: {{test_strategy}}
**Coverage**: {{coverage_metrics}}
**Component Status**: {{component_readiness}}
**Team Coordination**: {{team_status}}

Your role: Ensure quality, run integration tests.
Focus: {{current_focus}}"""
```

### **Template Variable Population**
```bash
# Search for template variables
agent-memory_search_memory_nodes --query "epic progress team status" --entity "Procedure"
agent-memory_search_memory_nodes --query "team assignments current" --entity "Procedure"
agent-memory_search_memory_facts --query "progress percentage component"

# Variables populated from memory searches:
# {{epic_name}} - Current epic being worked on
# {{team_progress}} - Overall team progress percentage
# {{component_status}} - Status of each component
# {{core_assignment}} - Tasks assigned to core builder
# {{published_interfaces}} - Available interfaces from core
# {{team_coordination}} - Current coordination state
```

## 🎯 **Advanced Memory Queries**

### **Progress Tracking Queries**
```bash
# Epic-level progress tracking
agent-memory_search_memory_nodes --query "epic progress milestone discord" --entity "Procedure"

# Component-specific progress
agent-memory_search_memory_nodes --query "core progress beta implementation" --entity "Procedure"
agent-memory_search_memory_nodes --query "api progress delta endpoints" --entity "Procedure"
agent-memory_search_memory_nodes --query "tool progress epsilon integration" --entity "Procedure"
agent-memory_search_memory_nodes --query "quality progress gamma testing" --entity "Procedure"

# Cross-component dependencies
agent-memory_search_memory_facts --query "component depends on interface"
```

### **Pattern Discovery Queries**
```bash
# Successful team patterns
agent-memory_search_memory_nodes --query "parallel team success pattern" --entity "Procedure"

# Component coordination patterns
agent-memory_search_memory_nodes --query "interface coordination pattern" --entity "Procedure"

# Quality patterns
agent-memory_search_memory_nodes --query "integration testing pattern" --entity "Procedure"
```

### **Blocker Resolution Queries**
```bash
# Identify current blockers
agent-memory_search_memory_nodes --query "blocked waiting dependency" --entity "Procedure"

# Find resolution patterns
agent-memory_search_memory_nodes --query "blocker resolution solution" --entity "Procedure"
```

## 🔧 **Memory Workflow Integration**

### **Git Integration with Memory**
```python
# Memory-informed commits
def commit_with_context():
    """Commit using memory context for better messages"""
    
    # Search for current work context
    context = agent-memory_search_memory_nodes(
        query="current progress task assignment",
        entity="Procedure"
    )
    
    # Commit using MCP tools with context
    git_add(
        repo_path="../am-agents-core",  # Component-specific worktree
        files=["src/agents/simple/discord/"]
    )
    git_commit(
        repo_path="../am-agents-core",
        message=f"feat(NMSTX-XX): {context.current_task} - {context.progress}"
    )
```

### **Linear Integration with Memory**
```bash
# Memory-informed Linear updates
# Search for current task status
agent-memory_search_memory_nodes --query "task progress current status" --entity "Procedure"

# Update Linear with memory context
linear_update_issue(
    id="NMSTX-XX",
    stateId="99291eb9-7768-4d3b-9778-d69d8de3f333",  # In Progress
    description="Progress: Based on memory search results"
)
```

## 📈 **Success Pattern Storage**

### **Team Success Patterns**
```bash
# Record successful parallel workflows
agent-memory_add_memory \
  --name "Parallel Success: Discord Epic" \
  --episode_body "5-agent parallel development completed Discord integration in 3 days vs estimated 15 days serial. Zero file conflicts. 4.8x efficiency gain." \
  --source "text"

# Record coordination improvements
agent-memory_add_memory \
  --name "MCP Coordination Pattern" \
  --episode_body "Direct MCP communication between agents reduced coordination overhead from 30% to 8%. Interface discovery via memory search eliminated wait times." \
  --source "text"
```

### **Component-Specific Patterns**
```bash
# Core development patterns
agent-memory_add_memory \
  --name "AutomagikAgent Extension Pattern" \
  --episode_body "Successful agent extension pattern: 1) Inherit from AutomagikAgent, 2) Set _code_prompt_text, 3) Configure dependencies, 4) Register tools, 5) Publish interfaces to memory" \
  --source "text"

# API development patterns
agent-memory_add_memory \
  --name "FastAPI Integration Pattern" \
  --episode_body "Parallel API development: 1) Discover core interfaces via memory, 2) Define endpoints based on interfaces, 3) Publish contracts to memory, 4) Test independently" \
  --source "text"
```

## 🚨 **Critical Memory Anti-Patterns**

### **❌ NEVER DO**
1. **Skip memory search** before starting component work
2. **Work without publishing interfaces** - breaks team coordination
3. **Ignore component dependencies** in memory
4. **Duplicate work** without checking existing patterns
5. **Skip progress updates** - breaks team visibility

### **✅ ALWAYS DO**
1. **Search memory first** for team assignments and coordination
2. **Publish interfaces immediately** when ready
3. **Update progress regularly** for team tracking
4. **Coordinate dependencies** via memory patterns
5. **Store successful patterns** for team reuse

---

**Remember**: Memory is the coordination backbone for parallel team development. Each agent uses memory to discover assignments, coordinate interfaces, track progress, and resolve dependencies. Effective memory usage enables true parallel development with minimal coordination overhead.
