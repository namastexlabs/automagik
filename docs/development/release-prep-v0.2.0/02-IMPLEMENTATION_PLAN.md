# Implementation Plan: release-prep-v0.2.0
## Claude Code Local-Only Transformation Execution Guide

### Overview for Implementation Workflow

This document provides the detailed execution plan for the **IMPLEMENT** workflow to transform Claude Code from dual-mode to local-only architecture. The plan is structured in 4 sequential phases with clear validation gates and success criteria.

---

## Phase 1: Immediate Deadcode Removal
**Duration**: 1 day  
**Risk Level**: LOW  
**Prerequisites**: Architecture review complete, implementation branch created  

### Objectives
- Remove all Docker-specific files and implementations
- Eliminate pure deadcode without affecting local execution
- Establish clean foundation for architecture simplification

### Tasks

#### Task 1.1: Remove Docker Implementation Files
```bash
# Remove Docker container implementation (346 lines)
rm src/agents/claude_code/container.py

# Remove Docker executor implementation (278 lines)
rm src/agents/claude_code/docker_executor.py

# Remove entire Docker configuration directory
rm -rf src/agents/claude_code/docker/
```

#### Task 1.2: Remove Docker Test Files
```bash
# Remove container tests (534 lines)
rm tests/agents/claude_code/test_container.py
```

#### Task 1.3: Update .gitignore Prevention
```bash
# Add to .gitignore to prevent future Docker artifacts
echo "# Prevent Docker artifacts in Claude Code
src/agents/claude_code/docker/
src/agents/claude_code/container.py
src/agents/claude_code/docker_executor.py
tests/agents/claude_code/test_container.py" >> .gitignore
```

#### Task 1.4: Remove Import References
Search and remove Docker imports that will break:
```bash
# Find Docker imports to remove
grep -r "from.*container import" src/agents/claude_code/
grep -r "from.*docker_executor import" src/agents/claude_code/
grep -r "import.*container" src/agents/claude_code/
```

### Validation Criteria
- [ ] All Docker files successfully removed (~1,158 lines)
- [ ] No broken imports in remaining codebase
- [ ] Basic functionality test passes:
  ```bash
  uv run python -c "from src.agents.claude_code.agent import ClaudeCodeAgent; print('Import successful')"
  ```
- [ ] Core test still passes:
  ```bash
  uv run pytest tests/agents/claude_code/test_agent.py::TestClaudeCodeAgentInitialization::test_agent_initialization -v
  ```

### Success Metrics
- **Codebase Reduction**: ~1,158 lines removed
- **Import Validation**: Zero import errors
- **Functionality Preserved**: Local execution unaffected

---

## Phase 2: Architecture Simplification  
**Duration**: 2 days  
**Risk Level**: MEDIUM  
**Prerequisites**: Phase 1 complete and validated  

### Objectives
- Simplify agent.py to direct LocalExecutor instantiation
- Remove or simplify ExecutorFactory pattern
- Implement graceful environment variable deprecation

### Tasks

#### Task 2.1: Simplify ClaudeCodeAgent Initialization
**File**: `src/agents/claude_code/agent.py`

**Remove (lines 97-110)**:
```python
# Determine execution mode
self.execution_mode = os.environ.get("CLAUDE_CODE_MODE", "local").lower()
logger.info(f"ClaudeCodeAgent initializing in {self.execution_mode} mode")

# Initialize appropriate executor
try:
    self.executor = ExecutorFactory.create_executor(
        mode=self.execution_mode,
        container_manager=self._create_container_manager() if self.execution_mode == "docker" else None,
        workspace_base=os.environ.get("CLAUDE_LOCAL_WORKSPACE", "/tmp/claude-workspace"),
        cleanup_on_complete=os.environ.get("CLAUDE_LOCAL_CLEANUP", "true").lower() == "true"
    )
except ValueError as e:
    logger.error(f"Failed to create executor: {e}")
    raise
```

**Replace with**:
```python
# Add deprecation warning for Docker mode
if os.environ.get("CLAUDE_CODE_MODE") == "docker":
    logger.warning(
        "CLAUDE_CODE_MODE=docker is deprecated and will be ignored. "
        "Claude Code now runs in local mode only. "
        "This warning will be removed in v0.3.0"
    )

# Initialize local executor directly
from .local_executor import LocalExecutor
self.executor = LocalExecutor(
    workspace_base=os.environ.get("CLAUDE_LOCAL_WORKSPACE", "/tmp/claude-workspace"),
    cleanup_on_complete=os.environ.get("CLAUDE_LOCAL_CLEANUP", "true").lower() == "true",
    git_cache_enabled=os.environ.get("CLAUDE_LOCAL_GIT_CACHE", "false").lower() == "true"
)
```

#### Task 2.2: Remove Container Manager Method
**File**: `src/agents/claude_code/agent.py`

**Remove method**:
```python
def _create_container_manager(self) -> ContainerManager:
    """Create container manager for Docker mode."""
    return ContainerManager(
        docker_image=self.config.get("docker_image"),
        container_timeout=self.config.get("container_timeout"),
        max_concurrent=self.config.get("max_concurrent_sessions")
    )
```

#### Task 2.3: Handle ExecutorFactory Decision
**Option A (Recommended)**: Remove ExecutorFactory entirely
- Remove `src/agents/claude_code/executor_factory.py`
- Remove factory imports from agent.py

**Option B**: Simplify to local-only utility
- Keep factory but remove Docker mode support
- Simplify to single `create_local_executor()` method

**Implementation Decision**: Choose Option A for maximum simplification

#### Task 2.4: Update Docker Configuration References
Remove Docker-specific configuration from agent initialization:
```python
# Remove from config dict:
"docker_image": config.get("docker_image", "claude-code-agent:latest"),
"container_timeout": int(config.get("container_timeout", "7200")),
"max_concurrent_sessions": int(config.get("max_concurrent_sessions", "10")),
"workspace_volume_prefix": config.get("workspace_volume_prefix", "claude-code-workspace"),
```

### Validation Criteria
- [ ] Agent initializes successfully with local executor only
- [ ] Deprecation warning appears when CLAUDE_CODE_MODE=docker
- [ ] No Docker-related imports remain
- [ ] All local execution tests pass
- [ ] Environment variable handling works correctly

### Success Metrics
- **Code Simplification**: Reduced complexity in agent initialization
- **Clean Architecture**: Single execution path from agent to executor
- **Backward Compatibility**: Graceful handling of deprecated configuration

---

## Phase 3: Test Suite Consolidation
**Duration**: 3 days  
**Risk Level**: MEDIUM-HIGH  
**Prerequisites**: Phase 2 complete and validated  

### Objectives
- Remove all Docker-specific test cases
- Consolidate overlapping local execution tests
- Enhance local execution edge case coverage
- Maintain 85%+ test coverage with improved performance

### Tasks

#### Task 3.1: Clean test_agent.py
**File**: `tests/agents/claude_code/test_agent.py`

**Remove Docker test methods**:
```python
# Remove if present:
def test_agent_initialization_docker_mode(self):
def test_agent_docker_container_creation(self):
def test_agent_docker_execution_flow(self):
def test_docker_mode_selection(self):
```

**Update existing tests**:
```python
# In test_agent_initialization, remove:
mock_container_class.assert_called_once_with(...)

# Keep only local executor assertions
```

#### Task 3.2: Refactor test_executor.py
**File**: `tests/agents/claude_code/test_executor.py`

**Remove Docker test class**:
```python
# Remove entire class:
class TestDockerExecutor:
    # All methods removed
```

**Simplify factory tests** (if keeping factory):
```python
class TestExecutorFactory:
    def test_create_local_executor_only(self):  # Renamed and simplified
        # Remove mode parameter testing
        # Focus only on local configuration validation
    
    # Remove:
    def test_create_docker_executor(self):
    def test_invalid_mode_handling(self):
    def test_docker_container_manager_requirement(self):
```

**Alternative**: Remove all factory tests if ExecutorFactory is removed

#### Task 3.3: Clean Integration Tests
**File**: `tests/agents/claude_code/test_integration.py`

**Remove Docker workflow tests**:
```python
# Remove if present:
@pytest.mark.integration
def test_docker_workflow_execution(self):
def test_container_isolation_integration(self):
def test_docker_environment_setup(self):
```

**Enhance local workflow tests**:
```python
@pytest.mark.integration
def test_local_workflow_execution_complete_cycle(self):
    """Comprehensive test of local workflow execution."""
    # Enhanced test covering:
    # - Workspace creation and cleanup
    # - Repository setup and branch handling
    # - Workflow configuration copying
    # - CLI execution and response handling
    # - Error handling and recovery
```

#### Task 3.4: Optimize Performance Tests
**File**: `tests/agents/claude_code/test_performance.py`

**Remove Docker performance comparisons**:
```python
# Remove:
def test_docker_vs_local_performance(self):
def test_container_startup_overhead(self):
def test_docker_memory_usage(self):
```

**Enhance local performance testing**:
```python
def test_local_executor_memory_efficiency(self):
    """Test memory usage during local execution."""
    
def test_local_workspace_creation_performance(self):
    """Benchmark workspace setup times."""
    
def test_large_repository_copy_performance(self):
    """Test performance with large repository copies."""
    
def test_concurrent_local_execution_performance(self):
    """Test multiple concurrent local executions."""
```

#### Task 3.5: Update Test Configuration
**File**: `tests/agents/claude_code/conftest.py`

Remove Docker-related fixtures and configuration:
```python
# Remove Docker fixtures if present:
@pytest.fixture
def docker_executor():
@pytest.fixture  
def container_manager():
@pytest.fixture
def docker_test_environment():
```

### Coverage Enhancement Strategy

#### Add Missing Local Edge Cases
1. **Error Handling Tests**:
   - Workspace creation failures
   - Repository setup errors
   - CLI execution timeouts
   - Environment variable edge cases

2. **Configuration Tests**:
   - Invalid workspace paths
   - Permission issues
   - Disk space limitations
   - Git repository edge cases

3. **Performance Edge Cases**:
   - Large file handling
   - Memory pressure scenarios
   - Concurrent execution limits
   - Cleanup failure recovery

### Validation Criteria
- [ ] Test coverage maintained at 85%+ (measure before/after)
- [ ] Test execution time improved by 20%+ 
- [ ] No Docker dependencies in test environment
- [ ] All local execution paths thoroughly tested
- [ ] Edge cases properly covered

### Success Metrics
- **Test Performance**: 20%+ improvement in execution time
- **Coverage Maintenance**: 85%+ coverage preserved
- **Test Quality**: Enhanced local execution scenario coverage
- **Clean Environment**: Zero Docker dependencies

---

## Phase 4: Project Rename Implementation
**Duration**: 1 day  
**Risk Level**: LOW  
**Prerequisites**: Phase 3 complete and validated  

### Objectives
- Rename project from "automagik-agents" to "automagik"
- Update all package references and metadata
- Ensure clean installation and import functionality

### Tasks

#### Task 4.1: Update Package Metadata
**File**: `pyproject.toml`

**Update project section**:
```toml
[project]
name = "automagik"  # Changed from "automagik-agents"
description = "Automagik AI agent framework and orchestration platform"
keywords = ["ai", "agents", "automation", "pydantic", "fastapi", "claude", "generative-ai", "orchestration"]

[project.urls]
Homepage = "https://github.com/namastexlabs/automagik"
Repository = "https://github.com/namastexlabs/automagik"
Issues = "https://github.com/namastexlabs/automagik/issues"
```

#### Task 4.2: Search and Replace Hardcoded References
```bash
# Find all hardcoded package name references
grep -r "automagik-agents" . --exclude-dir=.git --exclude-dir=.venv --exclude-dir=__pycache__
grep -r "automagik_agents" . --exclude-dir=.git --exclude-dir=.venv --exclude-dir=__pycache__

# Update found references to use "automagik"
```

#### Task 4.3: Update Documentation
**Files to update**:
- `README.md`: Title, description, installation instructions
- Documentation files: Package name references
- Installation guides: pip install commands

**Example changes**:
```bash
# Installation command update
# FROM: pip install automagik-agents
# TO:   pip install automagik
```

#### Task 4.4: Update Import Statements
Check for any hardcoded package name imports (should be rare):
```bash
# Search for potential hardcoded imports
grep -r "import automagik_agents" src/
grep -r "from automagik_agents" src/
```

### Validation Criteria
- [ ] Package builds successfully with new name
- [ ] Installation works: `pip install ./`
- [ ] Imports function correctly: `import automagik`
- [ ] No broken references to old package name
- [ ] Documentation reflects new name consistently

### Success Metrics
- **Clean Installation**: Package installs with new name
- **Functional Imports**: All import statements work correctly
- **Consistent Branding**: All references updated to new name

---

## Cross-Phase Validation Strategy

### Continuous Integration Checkpoints
After each phase, run comprehensive validation:

```bash
# Import validation
uv run python -c "from src.agents.claude_code.agent import ClaudeCodeAgent; print('✅ Import successful')"

# Core functionality test
uv run pytest tests/agents/claude_code/test_agent.py -v

# Coverage measurement
uv run pytest --cov=src/agents/claude_code tests/agents/claude_code/ --cov-report=term-missing

# Performance benchmark
time uv run pytest tests/agents/claude_code/ -q
```

### Quality Gates
- **Phase 1**: No import errors, basic functionality preserved
- **Phase 2**: Agent initialization works, deprecation warnings function
- **Phase 3**: 85%+ coverage maintained, 20%+ performance improvement
- **Phase 4**: Clean installation and import functionality

### Risk Mitigation Procedures

#### Emergency Rollback
```bash
# If any phase fails critically:
git stash  # Save current work
git checkout main  # Return to stable state
git branch implementation-backup  # Save progress
```

#### Common Issues and Solutions

**Hidden Docker Dependencies**:
```bash
# Search comprehensively before removal
grep -r -i "docker" src/ --exclude-dir=__pycache__
grep -r -i "container" src/ --exclude-dir=__pycache__ | grep -v "container_manager"
```

**Test Coverage Drop**:
- Add enhanced local execution test scenarios
- Focus on edge cases previously covered by Docker tests
- Use coverage reports to identify gaps

**Performance Regression**:
- Benchmark before each phase
- If performance degrades, investigate removed code for optimization
- Consider keeping performance-critical components

## Implementation Timeline

| Phase | Days | Start After | Dependencies |
|-------|------|-------------|--------------|
| Phase 1 | 1 | Architecture approval | None |
| Phase 2 | 2 | Phase 1 validation | Phase 1 complete |
| Phase 3 | 3 | Phase 2 validation | Phases 1-2 complete |
| Phase 4 | 1 | Phase 3 validation | Phases 1-3 complete |
| **Total** | **7 days** | **Sequential** | **All phases** |

## Success Declaration Criteria

### Technical Success
- [ ] ~1,000+ lines of deadcode removed
- [ ] Test coverage maintained at 85%+
- [ ] Test execution time improved by 20%+
- [ ] Zero Docker dependencies remaining
- [ ] Clean local-only architecture established

### Functional Success  
- [ ] All local Claude Code functionality preserved
- [ ] Workflow execution unaffected
- [ ] Environment variable handling works
- [ ] Project installation functions with new name

### Quality Success
- [ ] Clean, maintainable codebase
- [ ] Simplified architecture reduces complexity
- [ ] Enhanced documentation standards applied
- [ ] Comprehensive validation completed

**Implementation Workflow: Execute this plan sequentially with validation gates between each phase. Success in this implementation will establish a clean, maintainable, local-only Claude Code architecture ready for the 0.2 release.**