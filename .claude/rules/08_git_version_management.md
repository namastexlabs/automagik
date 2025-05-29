---
description: Git version management with MCP tools, parallel worktree coordination, and component-specific workflows for automagik-agents
globs: **/*
alwaysApply: true
---

# Git Version Management - Parallel Team Architecture

## 🚀 **Revolutionary Git Workflow**

**Transform from single-branch development to 5-agent parallel worktree development**

**Related**: [09_parallel_team_architecture.md](mdc:.cursor/rules/09_parallel_team_architecture.md) | [03_dev_workflow.md](mdc:.cursor/rules/03_dev_workflow.md)

**Target**: Enable true parallel development with zero conflicts through worktree isolation

## 🏗️ **Parallel Worktree Management**

### **Worktree Architecture**
```
/root/workspace/
├── am-agents-labs/          # Alpha Agent (main branch) - Orchestration
├── am-agents-core/          # Beta Agent (feature-core branch) - Core development
├── am-agents-api/           # Delta Agent (feature-api branch) - API development
├── am-agents-tools/         # Epsilon Agent (feature-tools branch) - Tool development
└── am-agents-tests/         # Gamma Agent (feature-tests branch) - Quality engineering
```

### **Worktree Initialization (Alpha Responsibility)**
```bash
# Alpha sets up parallel worktrees for epic development
cd /root/workspace/am-agents-labs

# Create component-specific worktrees
git worktree add ../am-agents-core feature-core
git worktree add ../am-agents-api feature-api
git worktree add ../am-agents-tools feature-tools
git worktree add ../am-agents-tests feature-tests

# Verify worktree structure
git worktree list

# Store worktree setup in memory
agent-memory_add_memory \
  --name "[P-GIT] Worktree Setup" \
  --episode_body "Parallel worktrees created: core, api, tools, tests - ready for 5-agent development" \
  --source "text"
```

### **Worktree Management Commands**
```bash
# List all worktrees
git worktree list

# Remove worktree (after epic completion)
git worktree remove ../am-agents-core
git worktree remove ../am-agents-api
git worktree remove ../am-agents-tools
git worktree remove ../am-agents-tests

# Prune deleted worktrees
git worktree prune
```

## 👥 **Component-Specific Git Workflows**

### **Alpha Agent - Orchestration Workflow** (main branch)
```python
# Alpha coordinates git operations across all worktrees
def alpha_git_workflow():
    """Alpha's git coordination responsibilities"""
    
    # 1. Check status across all worktrees
    main_status = mcp_git_git_status(repo_path="/root/workspace/am-agents-labs")
    core_status = mcp_git_git_status(repo_path="../am-agents-core")
    api_status = mcp_git_git_status(repo_path="../am-agents-api")
    tools_status = mcp_git_git_status(repo_path="../am-agents-tools")
    tests_status = mcp_git_git_status(repo_path="../am-agents-tests")
    
    # 2. Coordinate integration when components ready
    if all_components_ready():
        await coordinate_integration()
    
    # 3. Store coordination state
    agent-memory_add_memory(
        name="[P-GIT] Team Status",
        episode_body=f"Git status: Core {core_status}, API {api_status}, Tools {tools_status}, Tests {tests_status}",
        source="text"
    )

# Alpha integration coordination
def coordinate_integration():
    """Alpha orchestrates progressive integration"""
    
    # Switch to main for integration
    mcp_git_git_checkout(
        repo_path="/root/workspace/am-agents-labs",
        branch_name="main"
    )
    
    # Progressive merge strategy
    mcp_git_git_diff(
        repo_path="/root/workspace/am-agents-labs",
        target="feature-core"
    )
    
    # Merge components in dependency order
    # 1. Core first (foundation)
    # 2. API (depends on core)
    # 3. Tools (depends on core)
    # 4. Tests (depends on all)
```

### **Beta Agent - Core Development Workflow** (feature-core worktree)
```python
# Beta works in isolated core worktree
def beta_git_workflow():
    """Beta's core development git workflow"""
    
    # 1. Work in core worktree
    os.chdir("../am-agents-core")
    
    # 2. Check current status
    status = mcp_git_git_status(repo_path="../am-agents-core")
    
    # 3. Stage core changes
    mcp_git_git_add(
        repo_path="../am-agents-core",
        files=["src/agents/simple/discord/", "src/memory/"]
    )
    
    # 4. Commit with component prefix
    mcp_git_git_commit(
        repo_path="../am-agents-core",
        message="feat(NMSTX-XX-core): implement DiscordAgent with memory integration"
    )
    
    # 5. Store progress in memory
    agent-memory_add_memory(
        name="[P-CORE] Git Progress",
        episode_body="Core implementation committed: DiscordAgent, memory integration",
        source="text"
    )

# Beta interface publication workflow
def beta_interface_workflow():
    """Beta publishes interfaces for team coordination"""
    
    # Commit interface definitions
    mcp_git_git_add(
        repo_path="../am-agents-core",
        files=["src/agents/interfaces/", "src/schemas/"]
    )
    
    mcp_git_git_commit(
        repo_path="../am-agents-core",
        message="feat(NMSTX-XX-core): publish agent interfaces for team integration"
    )
    
    # Store interface publication
    agent-memory_add_memory(
        name="[P-CORE] Interface Publication",
        episode_body="Core interfaces committed and ready for team integration",
        source="text"
    )
```

### **Delta Agent - API Development Workflow** (feature-api worktree)
```python
# Delta works in isolated API worktree
def delta_git_workflow():
    """Delta's API development git workflow"""
    
    # 1. Work in API worktree
    os.chdir("../am-agents-api")
    
    # 2. Check for core interface updates
    mcp_git_git_diff(
        repo_path="../am-agents-api",
        target="feature-core"
    )
    
    # 3. Stage API changes
    mcp_git_git_add(
        repo_path="../am-agents-api",
        files=["src/api/routes/", "src/api/models/"]
    )
    
    # 4. Commit with component prefix
    mcp_git_git_commit(
        repo_path="../am-agents-api",
        message="feat(NMSTX-XX-api): implement Discord API endpoints with authentication"
    )
    
    # 5. Store progress in memory
    agent-memory_add_memory(
        name="[P-API] Git Progress",
        episode_body="API endpoints committed: Discord routes, authentication",
        source="text"
    )

# Delta API contract workflow
def delta_contract_workflow():
    """Delta publishes API contracts"""
    
    # Commit API documentation and contracts
    mcp_git_git_add(
        repo_path="../am-agents-api",
        files=["docs/api/", "src/api/schemas/"]
    )
    
    mcp_git_git_commit(
        repo_path="../am-agents-api",
        message="docs(NMSTX-XX-api): publish API contracts and documentation"
    )
```

### **Epsilon Agent - Tool Development Workflow** (feature-tools worktree)
```python
# Epsilon works in isolated tools worktree
def epsilon_git_workflow():
    """Epsilon's tool development git workflow"""
    
    # 1. Work in tools worktree
    os.chdir("../am-agents-tools")
    
    # 2. Stage tool implementations
    mcp_git_git_add(
        repo_path="../am-agents-tools",
        files=["src/tools/discord/", "src/tools/external/"]
    )
    
    # 3. Commit with component prefix
    mcp_git_git_commit(
        repo_path="../am-agents-tools",
        message="feat(NMSTX-XX-tools): implement Discord.py integration with async handling"
    )
    
    # 4. Store progress in memory
    agent-memory_add_memory(
        name="[P-TOOLS] Git Progress",
        episode_body="Tool integration committed: Discord.py, async handlers",
        source="text"
    )

# Epsilon tool registration workflow
def epsilon_registration_workflow():
    """Epsilon registers tools with core"""
    
    # Commit tool registration
    mcp_git_git_add(
        repo_path="../am-agents-tools",
        files=["src/tools/registry/", "src/tools/schemas/"]
    )
    
    mcp_git_git_commit(
        repo_path="../am-agents-tools",
        message="feat(NMSTX-XX-tools): register Discord tools with core registry"
    )
```

### **Gamma Agent - Quality Engineering Workflow** (feature-tests worktree)
```python
# Gamma works in isolated tests worktree
def gamma_git_workflow():
    """Gamma's quality engineering git workflow"""
    
    # 1. Work in tests worktree
    os.chdir("../am-agents-tests")
    
    # 2. Stage test implementations
    mcp_git_git_add(
        repo_path="../am-agents-tests",
        files=["tests/integration/", "tests/unit/"]
    )
    
    # 3. Commit with component prefix
    mcp_git_git_commit(
        repo_path="../am-agents-tests",
        message="test(NMSTX-XX-tests): add Discord integration test suite"
    )
    
    # 4. Store progress in memory
    agent-memory_add_memory(
        name="[P-TESTS] Git Progress",
        episode_body="Test suite committed: Discord integration, unit tests",
        source="text"
    )

# Gamma quality gate workflow
def gamma_quality_workflow():
    """Gamma validates quality gates"""
    
    # Commit quality reports
    mcp_git_git_add(
        repo_path="../am-agents-tests",
        files=["reports/coverage/", "reports/quality/"]
    )
    
    mcp_git_git_commit(
        repo_path="../am-agents-tests",
        message="test(NMSTX-XX-tests): quality gates passed - 95% coverage"
    )
```

## 🔄 **Progressive Integration Strategy**

### **Integration Sequence (Alpha Orchestration)**
```python
def progressive_integration():
    """Alpha orchestrates component integration in dependency order"""
    
    # 1. Verify component readiness
    component_status = check_component_readiness()
    
    if not all(component_status.values()):
        handle_incomplete_components(component_status)
        return False
    
    # 2. Switch to main branch
    mcp_git_git_checkout(
        repo_path="/root/workspace/am-agents-labs",
        branch_name="main"
    )
    
    # 3. Progressive merge in dependency order
    
    # Step 1: Merge core (foundation)
    mcp_git_git_diff(
        repo_path="/root/workspace/am-agents-labs",
        target="feature-core"
    )
    
    # Merge core if no conflicts
    run_terminal_cmd("git merge --no-ff feature-core -m 'feat(NMSTX-XX): integrate core component'")
    
    # Step 2: Merge API (depends on core)
    mcp_git_git_diff(
        repo_path="/root/workspace/am-agents-labs",
        target="feature-api"
    )
    
    run_terminal_cmd("git merge --no-ff feature-api -m 'feat(NMSTX-XX): integrate API component'")
    
    # Step 3: Merge tools (depends on core)
    mcp_git_git_diff(
        repo_path="/root/workspace/am-agents-labs",
        target="feature-tools"
    )
    
    run_terminal_cmd("git merge --no-ff feature-tools -m 'feat(NMSTX-XX): integrate tools component'")
    
    # Step 4: Merge tests (depends on all)
    mcp_git_git_diff(
        repo_path="/root/workspace/am-agents-labs",
        target="feature-tests"
    )
    
    run_terminal_cmd("git merge --no-ff feature-tests -m 'feat(NMSTX-XX): integrate tests component'")
    
    # 5. Final integration commit
    mcp_git_git_commit(
        repo_path="/root/workspace/am-agents-labs",
        message="feat(NMSTX-XX): complete parallel team integration - Discord epic"
    )
    
    # 6. Store integration success
    agent-memory_add_memory(
        name="[P-GIT] Integration Success",
        episode_body="Parallel team integration completed successfully - zero conflicts",
        source="text"
    )
    
    return True
```

### **Component Readiness Validation**
```python
def check_component_readiness():
    """Validate all components are ready for integration"""
    
    readiness = {}
    
    # Check core readiness (Beta)
    core_status = mcp_git_git_status(repo_path="../am-agents-core")
    readiness["core"] = "nothing to commit" in core_status
    
    # Check API readiness (Delta)
    api_status = mcp_git_git_status(repo_path="../am-agents-api")
    readiness["api"] = "nothing to commit" in api_status
    
    # Check tools readiness (Epsilon)
    tools_status = mcp_git_git_status(repo_path="../am-agents-tools")
    readiness["tools"] = "nothing to commit" in tools_status
    
    # Check tests readiness (Gamma)
    tests_status = mcp_git_git_status(repo_path="../am-agents-tests")
    readiness["tests"] = "nothing to commit" in tests_status
    
    # Store readiness state
    agent-memory_add_memory(
        name="[P-GIT] Component Readiness",
        episode_body=f"Component readiness: {readiness}",
        source="text"
    )
    
    return readiness
```

## 🚨 **Conflict Resolution by Component Expertise**

### **Conflict Resolution Strategy**
```python
def resolve_integration_conflicts():
    """Resolve conflicts based on component expertise"""
    
    # Check for conflicts during integration
    conflicts = mcp_git_git_status(repo_path="/root/workspace/am-agents-labs")
    
    if "unmerged paths" in conflicts:
        # Analyze conflict types
        conflict_analysis = analyze_conflicts(conflicts)
        
        # Route conflicts to component experts
        for conflict_file, conflict_type in conflict_analysis.items():
            if conflict_file.startswith("src/agents/") or conflict_file.startswith("src/memory/"):
                # Core conflicts: Beta agent expertise
                resolve_with_beta(conflict_file)
            elif conflict_file.startswith("src/api/"):
                # API conflicts: Delta agent expertise
                resolve_with_delta(conflict_file)
            elif conflict_file.startswith("src/tools/"):
                # Tool conflicts: Epsilon agent expertise
                resolve_with_epsilon(conflict_file)
            elif conflict_file.startswith("tests/"):
                # Test conflicts: Gamma agent expertise
                resolve_with_gamma(conflict_file)
            else:
                # General conflicts: Alpha coordination
                resolve_with_alpha(conflict_file)
        
        # Commit resolution
        mcp_git_git_add(
            repo_path="/root/workspace/am-agents-labs",
            files=["."]  # Add all resolved files
        )
        
        mcp_git_git_commit(
            repo_path="/root/workspace/am-agents-labs",
            message="fix(NMSTX-XX): resolve integration conflicts with component expertise"
        )
```

### **Component-Specific Conflict Resolution**
```bash
# Beta resolves core conflicts
def resolve_with_beta(conflict_file):
    """Beta resolves core-related conflicts"""
    # Beta has expertise in:
    # - AutomagikAgent implementations
    # - Memory system integration
    # - Core business logic
    # - Interface definitions
    
    # Search memory for core patterns
    agent-memory_search_memory_nodes --query "[P-CORE] conflict resolution pattern" --entity "Procedure"

# Delta resolves API conflicts
def resolve_with_delta(conflict_file):
    """Delta resolves API-related conflicts"""
    # Delta has expertise in:
    # - FastAPI endpoint definitions
    # - Authentication middleware
    # - Response models
    # - API documentation
    
    # Search memory for API patterns
    agent-memory_search_memory_nodes --query "[P-API] conflict resolution pattern" --entity "Procedure"

# Epsilon resolves tool conflicts
def resolve_with_epsilon(conflict_file):
    """Epsilon resolves tool-related conflicts"""
    # Epsilon has expertise in:
    # - External service integrations
    # - Tool implementations
    # - Async operations
    # - Error handling
    
    # Search memory for tool patterns
    agent-memory_search_memory_nodes --query "[P-TOOLS] conflict resolution pattern" --entity "Procedure"

# Gamma resolves test conflicts
def resolve_with_gamma(conflict_file):
    """Gamma resolves test-related conflicts"""
    # Gamma has expertise in:
    # - Integration test strategies
    # - Quality gates
    # - Mock implementations
    # - Coverage analysis
    
    # Search memory for test patterns
    agent-memory_search_memory_nodes --query "[P-TESTS] conflict resolution pattern" --entity "Procedure"
```

## 🏷️ **Enhanced Branch Naming for Epic Coordination**

### **Epic-Level Branch Naming**
```bash
# Epic coordination branches (Alpha)
NMSTX-123-epic-discord-integration     # Main epic coordination branch

# Component-specific branches
NMSTX-123-core-discord-agent          # Beta's core development
NMSTX-123-api-discord-endpoints       # Delta's API development  
NMSTX-123-tools-discord-integration   # Epsilon's tool development
NMSTX-123-tests-discord-suite         # Gamma's test development
```

### **Branch Creation Workflow**
```python
# Alpha creates epic coordination structure
def create_epic_branches(epic_id: str, epic_name: str):
    """Alpha creates coordinated branch structure"""
    
    # Create main epic branch
    mcp_git_git_create_branch(
        repo_path="/root/workspace/am-agents-labs",
        branch_name=f"NMSTX-{epic_id}-epic-{epic_name}",
        base_branch="main"
    )
    
    # Create component branches in worktrees
    mcp_git_git_create_branch(
        repo_path="../am-agents-core",
        branch_name=f"NMSTX-{epic_id}-core-{epic_name}",
        base_branch="feature-core"
    )
    
    mcp_git_git_create_branch(
        repo_path="../am-agents-api",
        branch_name=f"NMSTX-{epic_id}-api-{epic_name}",
        base_branch="feature-api"
    )
    
    mcp_git_git_create_branch(
        repo_path="../am-agents-tools",
        branch_name=f"NMSTX-{epic_id}-tools-{epic_name}",
        base_branch="feature-tools"
    )
    
    mcp_git_git_create_branch(
        repo_path="../am-agents-tests",
        branch_name=f"NMSTX-{epic_id}-tests-{epic_name}",
        base_branch="feature-tests"
    )
    
    # Store branch structure
    agent-memory_add_memory(
        name=f"[P-GIT] Epic Branch Structure: {epic_id}",
        episode_body=f"Epic branches created for {epic_name}: core, api, tools, tests",
        source="text"
    )
```

### **Commit Message Standards for Team Coordination**
```bash
# Component-specific commit prefixes
feat(NMSTX-XX-core): implement DiscordAgent with memory integration
feat(NMSTX-XX-api): add Discord API endpoints with authentication  
feat(NMSTX-XX-tools): integrate Discord.py with async handling
test(NMSTX-XX-tests): add Discord integration test suite

# Integration commits
feat(NMSTX-XX): integrate core component - interfaces published
feat(NMSTX-XX): integrate API component - endpoints ready
feat(NMSTX-XX): integrate tools component - Discord.py connected
feat(NMSTX-XX): integrate tests component - quality gates passed
feat(NMSTX-XX): complete parallel team integration - Discord epic
```

## 📊 **Git Metrics for Parallel Development**

### **Team Coordination Metrics**
```bash
# Track parallel development efficiency
agent-memory_add_memory \
  --name "[P-GIT] Parallel Efficiency Metrics" \
  --episode_body "{\"epic\": \"discord-integration\", \"parallel_commits\": 47, \"conflicts\": 0, \"integration_time\": \"15_minutes\", \"efficiency_gain\": \"4.8x\"}" \
  --source "json"

# Track component contribution
agent-memory_add_memory \
  --name "[P-GIT] Component Contributions" \
  --episode_body "{\"core_commits\": 12, \"api_commits\": 8, \"tools_commits\": 15, \"tests_commits\": 12, \"total_parallel_commits\": 47}" \
  --source "json"
```

### **Integration Success Patterns**
```bash
# Store successful integration patterns
agent-memory_add_memory \
  --name "[P-GIT] Integration Success Pattern" \
  --episode_body "Successful parallel integration: Core first → API second → Tools third → Tests fourth → Zero conflicts → 15 minute integration time" \
  --source "text"

# Store conflict prevention patterns
agent-memory_add_memory \
  --name "[P-GIT] Conflict Prevention Pattern" \
  --episode_body "Conflict prevention: Worktree isolation + Component specialization + Interface coordination + Progressive integration = Zero conflicts" \
  --source "text"
```

## 🔧 **Git Troubleshooting for Parallel Teams**

### **Common Parallel Development Issues**
```bash
# Worktree synchronization issues
git worktree list                    # Check worktree status
git worktree prune                   # Clean up deleted worktrees

# Component readiness validation
mcp_git_git_status(repo_path="../am-agents-core")
mcp_git_git_status(repo_path="../am-agents-api")
mcp_git_git_status(repo_path="../am-agents-tools")
mcp_git_git_status(repo_path="../am-agents-tests")

# Integration preparation
mcp_git_git_diff(repo_path="/root/workspace/am-agents-labs", target="feature-core")
mcp_git_git_diff(repo_path="/root/workspace/am-agents-labs", target="feature-api")
mcp_git_git_diff(repo_path="/root/workspace/am-agents-labs", target="feature-tools")
mcp_git_git_diff(repo_path="/root/workspace/am-agents-labs", target="feature-tests")
```

### **Recovery Procedures**
```bash
# If integration fails, reset and retry
mcp_git_git_reset(repo_path="/root/workspace/am-agents-labs")

# If worktree corruption, recreate
git worktree remove ../am-agents-core
git worktree add ../am-agents-core feature-core

# If conflicts persist, use component expertise
# Route to appropriate agent based on file paths
```

---

**Remember**: This parallel git workflow enables true simultaneous development through worktree isolation. Each agent works independently in their specialized worktree while Alpha coordinates progressive integration. The result is zero conflicts and 5x development speed through expert specialization and coordinated integration. 