---
description: Parallel team development workflow with 5 specialized agents and mode switching for automagik-agents
globs: **/*
alwaysApply: true
---

# Parallel Team Development Workflow

## 🚀 **Revolutionary Parallel Architecture**

**Transform from single-agent serial development to 5-agent parallel development**

**Related**: [09_parallel_team_architecture.md](mdc:.cursor/rules/09_parallel_team_architecture.md) | [08_git_version_management.md](mdc:.cursor/rules/08_git_version_management.md)

**Target**: **5x development speed** through specialized agent coordination

## 👥 **Team Agent Workflows**

### **Alpha Agent - Orchestrator** (main branch)
**Mission**: Epic coordination, task distribution, integration oversight

#### **Alpha Workflow**
```python
# 1. Epic Analysis & Breakdown
async def orchestrate_epic(epic_id: str):
    """Alpha's primary workflow"""
    
    # Search memory for similar epics
    agent-memory_search_memory_nodes(
        query="epic breakdown pattern similar requirements",
        entity="Procedure"
    )
    
    # Analyze epic requirements
    epic_analysis = await analyze_epic_requirements(epic_id)
    
    # Break into component tasks
    component_tasks = {
        "core": await create_core_tasks(epic_analysis),
        "api": await create_api_tasks(epic_analysis),
        "tools": await create_tool_tasks(epic_analysis),
        "tests": await create_test_tasks(epic_analysis)
    }
    
    # Assign to specialized agents via MCP
    for component, tasks in component_tasks.items():
        await coordinate_with_team(f"{component}-agent", {
            "type": "task_assignment",
            "epic": epic_id,
            "tasks": tasks,
            "priority": "high"
        })
    
    # Store epic coordination pattern
    agent-memory_add_memory(
        name=f"[P-EPIC] Epic Breakdown: {epic_id}",
        episode_body=f"Epic {epic_id} broken into {len(component_tasks)} parallel streams",
        source="text"
    )
```

#### **Alpha Daily Workflow**
```bash
# Morning: Epic coordination
agent-memory_search_memory_nodes --query "[P-EPIC] active epic status" --entity "Procedure"
linear_list_my_issues --limit 20

# Continuous: Team coordination
# Monitor team progress via MCP
# Resolve blockers between components
# Coordinate interface contracts

# Evening: Integration planning
agent-memory_search_memory_nodes --query "[P-CORE] [P-API] [P-TOOLS] [P-TESTS] ready" --entity "Procedure"
```

### **Beta Agent - Core Builder** (feature-core worktree)
**Mission**: Core framework, agents, memory systems

#### **Beta Workflow**
```python
# 1. Core Development in Isolation
async def develop_core_component(task_assignment: dict):
    """Beta's specialized core development"""
    
    # Switch to core worktree
    os.chdir("../am-agents-core")
    
    # Search for core patterns
    agent-memory_search_memory_nodes(
        query="AutomagikAgent extension pattern tool registry",
        entity="Procedure"
    )
    
    # Implement core feature
    await implement_core_feature(task_assignment)
    
    # Store core patterns
    agent-memory_add_memory(
        name=f"[P-CORE] {task_assignment['feature']} Pattern",
        episode_body=f"Core implementation: {task_assignment['description']}",
        source="text"
    )
    
    # Publish interfaces for team
    await publish_core_interfaces(task_assignment)
    
    # Signal completion to Alpha
    await coordinate_with_team("alpha-orchestrator", {
        "type": "component_complete",
        "component": "core",
        "task": task_assignment["task_id"],
        "interfaces": await get_published_interfaces()
    })
```

#### **Beta Daily Workflow**
```bash
# Morning: Core development focus
cd ../am-agents-core
agent-memory_search_memory_nodes --query "[P-CORE] agent pattern implementation" --entity "Procedure"

# Development: Core implementation
# Extend AutomagikAgent classes
# Implement memory integrations
# Create tool registries
# Publish interfaces to memory

# Evening: Interface coordination
agent-memory_add_memory \
  --name "[P-CORE] Interface Publication" \
  --episode_body "Published core interfaces for team integration" \
  --source "text"
```

### **Delta Agent - API Builder** (feature-api worktree)
**Mission**: FastAPI endpoints, authentication, middleware

#### **Delta Workflow**
```python
# 1. API Development with Core Integration
async def develop_api_component(task_assignment: dict):
    """Delta's specialized API development"""
    
    # Switch to API worktree
    os.chdir("../am-agents-api")
    
    # Search for API patterns
    agent-memory_search_memory_nodes(
        query="FastAPI endpoint authentication pattern",
        entity="Procedure"
    )
    
    # Get core interfaces from Beta
    core_interfaces = await get_core_interfaces_from_memory()
    
    # Implement API endpoints
    await implement_api_endpoints(task_assignment, core_interfaces)
    
    # Store API patterns
    agent-memory_add_memory(
        name=f"[P-API] {task_assignment['endpoint']} Pattern",
        episode_body=f"API endpoint: {task_assignment['description']}",
        source="text"
    )
    
    # Signal completion to Alpha
    await coordinate_with_team("alpha-orchestrator", {
        "type": "component_complete",
        "component": "api",
        "task": task_assignment["task_id"],
        "endpoints": await get_implemented_endpoints()
    })
```

#### **Delta Daily Workflow**
```bash
# Morning: API development focus
cd ../am-agents-api
agent-memory_search_memory_nodes --query "[P-API] endpoint authentication pattern" --entity "Procedure"

# Development: API implementation
# Create FastAPI endpoints
# Implement authentication
# Add response models
# Integrate with core interfaces

# Evening: API documentation
agent-memory_add_memory \
  --name "[P-API] Endpoint Documentation" \
  --episode_body "Updated API documentation with new endpoints" \
  --source "text"
```

### **Epsilon Agent - Tool Builder** (feature-tools worktree)
**Mission**: External integrations, tool development

#### **Epsilon Workflow**
```python
# 1. Tool Development with External Services
async def develop_tool_component(task_assignment: dict):
    """Epsilon's specialized tool development"""
    
    # Switch to tools worktree
    os.chdir("../am-agents-tools")
    
    # Search for tool patterns
    agent-memory_search_memory_nodes(
        query="external integration async pattern",
        entity="Procedure"
    )
    
    # Implement tool integration
    await implement_tool_integration(task_assignment)
    
    # Store tool patterns
    agent-memory_add_memory(
        name=f"[P-TOOLS] {task_assignment['service']} Integration",
        episode_body=f"Tool integration: {task_assignment['description']}",
        source="text"
    )
    
    # Signal completion to Alpha
    await coordinate_with_team("alpha-orchestrator", {
        "type": "component_complete",
        "component": "tools",
        "task": task_assignment["task_id"],
        "tools": await get_implemented_tools()
    })
```

#### **Epsilon Daily Workflow**
```bash
# Morning: Tool development focus
cd ../am-agents-tools
agent-memory_search_memory_nodes --query "[P-TOOLS] integration pattern async" --entity "Procedure"

# Development: Tool implementation
# Create external service integrations
# Implement async operations
# Add error handling
# Register tools with core

# Evening: Integration testing
agent-memory_add_memory \
  --name "[P-TOOLS] Integration Testing" \
  --episode_body "Completed tool integration testing" \
  --source "text"
```

### **Gamma Agent - Quality Engineer** (feature-tests worktree)
**Mission**: Testing, quality assurance, documentation

#### **Gamma Workflow**
```python
# 1. Quality Engineering Across All Components
async def develop_quality_component(task_assignment: dict):
    """Gamma's specialized quality engineering"""
    
    # Switch to tests worktree
    os.chdir("../am-agents-tests")
    
    # Search for testing patterns
    agent-memory_search_memory_nodes(
        query="integration test pattern mock dependencies",
        entity="Procedure"
    )
    
    # Implement comprehensive testing
    await implement_integration_tests(task_assignment)
    
    # Store testing patterns
    agent-memory_add_memory(
        name=f"[P-TESTS] {task_assignment['test_type']} Pattern",
        episode_body=f"Test implementation: {task_assignment['description']}",
        source="text"
    )
    
    # Signal completion to Alpha
    await coordinate_with_team("alpha-orchestrator", {
        "type": "component_complete",
        "component": "tests",
        "task": task_assignment["task_id"],
        "coverage": await get_test_coverage()
    })
```

#### **Gamma Daily Workflow**
```bash
# Morning: Quality engineering focus
cd ../am-agents-tests
agent-memory_search_memory_nodes --query "[P-TESTS] integration test coverage" --entity "Procedure"

# Development: Test implementation
# Create integration tests
# Add unit test coverage
# Implement quality gates
# Update documentation

# Evening: Quality metrics
agent-memory_add_memory \
  --name "[P-TESTS] Quality Metrics" \
  --episode_body "Updated quality metrics and coverage reports" \
  --source "text"
```

## 🔄 **Parallel Coordination Workflows**

### **Daily Team Synchronization**
```bash
# Alpha coordinates daily sync
agent-memory_search_memory_nodes --query "[P-EPIC] [P-CORE] [P-API] [P-TOOLS] [P-TESTS] progress" --max_nodes 20

# Each agent reports status
agent-memory_add_memory \
  --name "[P-TEAM] Daily Sync $(date)" \
  --episode_body "Team progress: Core 80%, API 60%, Tools 70%, Tests 50%" \
  --source "text"
```

### **Interface Coordination Protocol**
```python
# Beta publishes core interfaces
async def publish_core_interfaces():
    """Beta makes interfaces available to team"""
    
    interfaces = await extract_core_interfaces()
    
    # Store in memory for team access
    agent-memory_add_memory(
        name="[P-INTERFACE] Core Interfaces",
        episode_body=json.dumps(interfaces),
        source="json"
    )
    
    # Notify team via MCP
    await mcp_broadcast("core_interfaces_ready", interfaces)

# Delta queries and uses core interfaces
async def integrate_with_core():
    """Delta builds APIs based on core interfaces"""
    
    # Search for published interfaces
    result = agent-memory_search_memory_nodes(
        query="core interfaces published",
        entity="Procedure"
    )
    
    # Build API endpoints based on discovered interfaces
    await build_api_endpoints(result.interfaces)
```

### **Progressive Integration Strategy**
```bash
# 1. Component readiness check
agent-memory_search_memory_nodes --query "[P-CORE] [P-API] [P-TOOLS] [P-TESTS] complete" --entity "Procedure"

# 2. Interface validation
agent-memory_search_memory_facts --query "interface contract validated"

# 3. Progressive merge (Alpha responsibility)
git checkout main
git merge feature-core    # Beta's work
git merge feature-api     # Delta's work
git merge feature-tools   # Epsilon's work
git merge feature-tests   # Gamma's work

# 4. Final integration testing
pytest tests/integration/parallel_team/
```

## 🎯 **Mode Switching for Specialized Work**

### **Alpha Mode - Epic Orchestration**
```bash
# Epic breakdown and coordination
ALPHA_MODE="orchestration"

# Focus areas:
# - Epic analysis and breakdown
# - Task assignment via MCP
# - Team progress monitoring
# - Integration coordination
# - Blocker resolution

# Memory patterns:
agent-memory_search_memory_nodes --query "epic breakdown coordination pattern" --entity "Procedure"
```

### **Beta Mode - Core Development**
```bash
# Core framework development
BETA_MODE="core_development"

# Focus areas:
# - AutomagikAgent extensions
# - Memory system integration
# - Core infrastructure
# - Interface publication

# Memory patterns:
agent-memory_search_memory_nodes --query "AutomagikAgent extension pattern" --entity "Procedure"
```

### **Delta Mode - API Development**
```bash
# API endpoint development
DELTA_MODE="api_development"

# Focus areas:
# - FastAPI endpoint creation
# - Authentication implementation
# - Response model design
# - OpenAPI documentation

# Memory patterns:
agent-memory_search_memory_nodes --query "FastAPI endpoint authentication" --entity "Procedure"
```

### **Epsilon Mode - Tool Integration**
```bash
# External tool development
EPSILON_MODE="tool_integration"

# Focus areas:
# - External service integrations
# - Async operation handling
# - Tool registry management
# - Error handling patterns

# Memory patterns:
agent-memory_search_memory_nodes --query "external integration async pattern" --entity "Procedure"
```

### **Gamma Mode - Quality Engineering**
```bash
# Quality assurance and testing
GAMMA_MODE="quality_engineering"

# Focus areas:
# - Integration test development
# - Quality gate implementation
# - Documentation updates
# - Coverage analysis

# Memory patterns:
agent-memory_search_memory_nodes --query "integration test coverage pattern" --entity "Procedure"
```

## 🧠 **Memory-Driven Coordination**

### **Component-Specific Memory Patterns**
```bash
# Search for component patterns before starting work
agent-memory_search_memory_nodes --query "[P-CORE] agent extension pattern" --entity "Procedure"
agent-memory_search_memory_nodes --query "[P-API] endpoint authentication" --entity "Procedure"
agent-memory_search_memory_nodes --query "[P-TOOLS] integration async" --entity "Procedure"
agent-memory_search_memory_nodes --query "[P-TESTS] coverage strategy" --entity "Procedure"

# Store new patterns immediately
agent-memory_add_memory \
  --name "[P-CORE] New Agent Pattern" \
  --episode_body "Discovered new AutomagikAgent extension pattern" \
  --source "text"
```

### **Cross-Component Dependencies**
```bash
# Track dependencies between components
agent-memory_search_memory_facts --query "depends on requires interface"

# Store interface contracts
agent-memory_add_memory \
  --name "[P-INTERFACE] Core-API Contract" \
  --episode_body "{\"endpoint\": \"/api/v1/agents\", \"requires\": \"AutomagikAgent\"}" \
  --source "json"
```

## 🚀 **Team Startup & Coordination**

### **Parallel Team Initialization**
```bash
# Start parallel team (Alpha responsibility)
./scripts/start_parallel_team.sh

# Verify team status
agent-memory_search_memory_nodes --query "[P-TEAM] startup status" --entity "Procedure"

# Check MCP communication
# Alpha: localhost:3001
# Beta: localhost:3002  
# Delta: localhost:3003
# Epsilon: localhost:3004
# Gamma: localhost:3005
```

### **Epic Launch Sequence**
```python
# Alpha receives epic and launches team
async def launch_epic(epic_id: str):
    """Alpha launches parallel epic development"""
    
    # 1. Create Linear epic
    epic = linear_create_issue(
        title=f"📋 Epic: {epic_id}",
        teamId="2c6b21de-9db7-44ac-9666-9079ff5b9b84",
        projectId="dbb25a78-ffce-45ba-af9c-898b35255896"
    )
    
    # 2. Break into component tasks
    component_tasks = await break_epic_into_components(epic_id)
    
    # 3. Assign to specialized agents
    for agent, tasks in component_tasks.items():
        await assign_tasks_to_agent(agent, tasks)
    
    # 4. Store epic coordination
    agent-memory_add_memory(
        name=f"[P-EPIC] Epic Launch: {epic_id}",
        episode_body=f"Epic {epic_id} launched with {len(component_tasks)} parallel streams",
        source="text"
    )
```

## 📊 **Success Metrics & Quality Gates**

### **Development Speed Metrics**
```bash
# Track epic completion times
agent-memory_add_memory \
  --name "[P-METRICS] Epic Performance" \
  --episode_body "{\"epic\": \"discord-integration\", \"completion_time\": \"2_days\", \"team_efficiency\": \"4.2x\"}" \
  --source "json"

# Monitor parallel efficiency
agent-memory_search_memory_nodes --query "[P-TEAM] efficiency metrics" --entity "Procedure"
```

### **Quality Gates by Component**
```python
QUALITY_GATES = {
    "core": [
        "AutomagikAgent extensions follow pattern",
        "Memory integration tests pass",
        "Core interfaces published"
    ],
    "api": [
        "All endpoints have authentication",
        "Response models validated",
        "OpenAPI documentation complete"
    ],
    "tools": [
        "External integrations tested",
        "Error handling implemented",
        "Tool registry updated"
    ],
    "tests": [
        "Integration tests cover all components",
        "Quality metrics meet thresholds",
        "Documentation updated"
    ]
}
```

## 🔧 **Troubleshooting Parallel Development**

### **Common Coordination Issues**
```bash
# MCP communication problems
# Check MCP server status for each agent
ps aux | grep mcp

# Memory coordination issues
agent-memory_search_memory_nodes --query "[P-TEAM] coordination problem" --entity "Procedure"

# Interface contract conflicts
agent-memory_search_memory_facts --query "interface conflict resolution"
```

### **Integration Conflict Resolution**
```bash
# If conflicts occur during integration
git checkout main
git merge --no-ff feature-core

# Resolve based on component expertise:
# Core conflicts: Beta agent expertise
# API conflicts: Delta agent expertise
# Tool conflicts: Epsilon agent expertise
# Test conflicts: Gamma agent expertise
```

---

**Remember**: This parallel workflow enables 5x development speed through specialized agent coordination. Each agent works in isolation while maintaining team coordination through MCP communication and memory sharing. The result is true parallel development with zero conflicts and expert specialization.
