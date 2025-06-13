# Detailed Cleanup Execution Plan
## Epic: release-prep-v0.2.0 - Claude Code Local-Only Transformation

### Ultra-Deep Analysis Results

After comprehensive codebase analysis, this document provides the detailed execution plan for transforming Claude Code to local-only architecture with complete deadcode removal and test suite optimization.

### Deadcode Analysis - Complete Inventory

#### Category A: Immediate Deletion (Zero Dependencies)
```
src/agents/claude_code/docker/
├── Dockerfile                     # Docker container configuration
├── docker-compose.yml            # Docker Compose setup  
└── entrypoint.sh                 # Container entry point script

src/agents/claude_code/
├── container.py                  # ContainerManager class (346 lines)
└── docker_executor.py           # DockerExecutor implementation (278 lines)

tests/agents/claude_code/
└── test_container.py            # Container tests (534 lines)
```
**Total Deadcode**: ~1,158 lines of pure Docker implementation

#### Category B: Refactor Required (Mixed Concerns)
```
src/agents/claude_code/
├── agent.py                     # Lines 97-110: Docker mode logic
├── executor_factory.py         # Lines 47-54: Docker executor creation
└── executor_base.py            # Abstract base (may be simplified)

tests/agents/claude_code/
├── test_agent.py               # Docker test cases scattered throughout
├── test_executor.py            # Mixed executor tests (Docker portions)
├── test_integration.py         # Docker integration scenarios
└── test_performance.py        # Docker performance benchmarks
```

#### Category C: Configuration Cleanup
```
Environment Variables (mark as deprecated):
- CLAUDE_CODE_MODE             # "docker"|"local" selector
- Docker-related configs in workflow .env files

Documentation References:
- Docker setup instructions
- Container troubleshooting guides
- Docker deployment examples
```

### Test Suite Deep Analysis

#### Test File Categorization

**1. test_container.py (FULL REMOVAL)**
- 534 lines of pure Docker container testing
- ContainerManager lifecycle tests
- Docker integration scenarios
- Zero relevance to local-only architecture

**2. test_executor.py (PARTIAL REFACTOR)**
Current structure:
```python
class TestExecutorFactory:          # Mixed mode testing
class TestDockerExecutor:           # REMOVE
class TestLocalExecutor:            # KEEP & ENHANCE
class TestExecutorIntegration:      # SIMPLIFY (remove Docker paths)
```

**3. test_agent.py (SURGICAL REFACTOR)**
Lines requiring changes:
```python
# REMOVE Docker mode tests
@patch.dict('os.environ', {'CLAUDE_CODE_MODE': 'docker'})
def test_agent_initialization_docker_mode(self):

# SIMPLIFY to local-only
def test_agent_initialization(self):
    # Remove container_manager assertions
    # Focus on local executor initialization
```

**4. test_integration.py (FOCUSED CLEANUP)**
- Remove Docker workflow execution tests
- Keep local workflow execution tests
- Simplify environment setup tests

**5. test_performance.py (BENCHMARK FOCUS)**
- Remove Docker performance comparisons
- Focus on local execution optimization
- Maintain memory usage benchmarks

### Execution Sequence - Phase-by-Phase

#### Phase 1: Immediate Deadcode Removal
**Duration**: 1 day
**Risk Level**: LOW

**Step 1.1: Remove Pure Docker Files**
```bash
# Remove Docker implementation files
rm -rf src/agents/claude_code/docker/
rm src/agents/claude_code/container.py
rm src/agents/claude_code/docker_executor.py

# Remove Docker test files
rm tests/agents/claude_code/test_container.py

# Remove Docker references from conftest.py if any
grep -n "docker" tests/agents/claude_code/conftest.py
```

**Step 1.2: Update .gitignore**
```gitignore
# Prevent future Docker artifacts
src/agents/claude_code/docker/
**/docker_executor.py
**/container.py
tests/**/test_container.py
```

**Step 1.3: Verify Removal**
```bash
# Ensure no imports break
python -c "from src.agents.claude_code.agent import ClaudeCodeAgent"

# Run basic test to ensure system still works
pytest tests/agents/claude_code/test_agent.py::TestClaudeCodeAgentInitialization::test_agent_initialization -v
```

#### Phase 2: Architecture Simplification
**Duration**: 2 days
**Risk Level**: MEDIUM

**Step 2.1: Simplify agent.py**
Remove lines 97-110 (Docker mode logic):
```python
# REMOVE:
self.execution_mode = os.environ.get("CLAUDE_CODE_MODE", "local").lower()
logger.info(f"ClaudeCodeAgent initializing in {self.execution_mode} mode")

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

# REPLACE WITH:
from .local_executor import LocalExecutor

self.executor = LocalExecutor(
    workspace_base=os.environ.get("CLAUDE_LOCAL_WORKSPACE", "/tmp/claude-workspace"),
    cleanup_on_complete=os.environ.get("CLAUDE_LOCAL_CLEANUP", "true").lower() == "true",
    git_cache_enabled=os.environ.get("CLAUDE_LOCAL_GIT_CACHE", "false").lower() == "true"
)
```

**Step 2.2: Handle ExecutorFactory Decision**
Option A: Simplify to local-only factory
Option B: Remove factory entirely (RECOMMENDED)

```python
# If keeping factory, simplify to:
class ExecutorFactory:
    @staticmethod
    def create_local_executor(**kwargs) -> LocalExecutor:
        workspace_base = kwargs.get('workspace_base', 
                                  os.environ.get("CLAUDE_LOCAL_WORKSPACE", "/tmp/claude-workspace"))
        cleanup_on_complete = kwargs.get('cleanup_on_complete',
                                       os.environ.get("CLAUDE_LOCAL_CLEANUP", "true").lower() == "true")
        git_cache_enabled = kwargs.get('git_cache_enabled',
                                     os.environ.get("CLAUDE_LOCAL_GIT_CACHE", "false").lower() == "true")
        
        return LocalExecutor(
            workspace_base=workspace_base,
            cleanup_on_complete=cleanup_on_complete,
            git_cache_enabled=git_cache_enabled
        )
```

**Step 2.3: Remove _create_container_manager method**
```python
# REMOVE from agent.py:
def _create_container_manager(self) -> ContainerManager:
    """Create container manager for Docker mode."""
    return ContainerManager(
        docker_image=self.config.get("docker_image"),
        container_timeout=self.config.get("container_timeout"),
        max_concurrent=self.config.get("max_concurrent_sessions")
    )
```

#### Phase 3: Test Suite Consolidation
**Duration**: 3 days
**Risk Level**: MEDIUM-HIGH

**Step 3.1: Clean test_agent.py**
```python
# REMOVE Docker test methods:
def test_agent_initialization_docker_mode(self):
def test_agent_docker_container_creation(self):
def test_agent_docker_execution_flow(self):

# UPDATE remaining tests to remove Docker assertions:
def test_agent_initialization(self):
    # Remove:
    mock_container_class.assert_called_once_with(...)
    
    # Keep local executor assertions only
```

**Step 3.2: Refactor test_executor.py**
```python
# REMOVE entire Docker test class:
class TestDockerExecutor:
    # All methods removed

# SIMPLIFY factory tests:
class TestExecutorFactory:
    def test_create_local_executor(self):  # Renamed from test_create_executor
        # Remove mode parameter testing
        # Focus on local configuration validation
        
    # REMOVE:
    def test_create_docker_executor(self):
    def test_invalid_mode_handling(self):
```

**Step 3.3: Clean test_integration.py**
Focus on local workflow integration only:
```python
# REMOVE Docker workflow tests:
@pytest.mark.integration
def test_docker_workflow_execution(self):

# ENHANCE local workflow tests:
@pytest.mark.integration  
def test_local_workflow_execution_complete_cycle(self):
    # Comprehensive local execution validation
```

**Step 3.4: Optimize test_performance.py**
```python
# REMOVE Docker performance comparisons:
def test_docker_vs_local_performance(self):
def test_container_startup_overhead(self):

# ENHANCE local performance testing:
def test_local_executor_memory_efficiency(self):
def test_local_workspace_creation_performance(self):
def test_large_repository_copy_performance(self):
```

#### Phase 4: Project Rename Implementation
**Duration**: 1 day
**Risk Level**: LOW

**Step 4.1: Update pyproject.toml**
```toml
[project]
name = "automagik"  # Changed from "automagik-agents"
description = "Automagik AI agent framework and orchestration platform"
keywords = ["ai", "agents", "automation", "pydantic", "fastapi", "claude", "generative-ai"]

# Update URLs if needed
[project.urls]
Homepage = "https://github.com/namastexlabs/automagik"
Repository = "https://github.com/namastexlabs/automagik"
Issues = "https://github.com/namastexlabs/automagik/issues"
```

**Step 4.2: Update Package References**
Search for hardcoded package name references:
```bash
grep -r "automagik-agents" . --exclude-dir=.git --exclude-dir=.venv
grep -r "automagik_agents" . --exclude-dir=.git --exclude-dir=.venv
```

**Step 4.3: Update Documentation**
- README.md title and description
- Installation instructions
- Docker documentation removal

### Risk Mitigation Strategies

#### Risk 1: Hidden Docker Dependencies
**Mitigation**: 
- Comprehensive grep for Docker references
- Import testing after each phase
- Gradual rollout with checkpoints

**Validation Commands**:
```bash
# Search for hidden Docker dependencies
grep -r -i "docker" src/ --exclude-dir=__pycache__
grep -r -i "container" src/ --exclude-dir=__pycache__ | grep -v "container_manager"
```

#### Risk 2: Test Coverage Reduction
**Mitigation**:
- Maintain detailed coverage metrics
- Enhance local test scenarios
- Add edge case coverage for local-only paths

**Coverage Validation**:
```bash
# Before cleanup
pytest --cov=src/agents/claude_code tests/agents/claude_code/ --cov-report=term-missing

# After cleanup (target: maintain 85%+ coverage)
pytest --cov=src/agents/claude_code tests/agents/claude_code/ --cov-report=term-missing
```

#### Risk 3: Breaking Changes for Users
**Mitigation**:
- Maintain environment variable compatibility
- Provide clear migration documentation
- Graceful handling of deprecated configs

**Compatibility Layer**:
```python
# In agent.py - deprecation warning for Docker mode
if os.environ.get("CLAUDE_CODE_MODE") == "docker":
    logger.warning(
        "Docker mode is deprecated and will be ignored. "
        "Claude Code now runs in local mode only. "
        "This warning will be removed in v0.3.0"
    )
```

### Quality Assurance Protocol

#### Pre-Implementation Checklist
- [ ] Complete backup of current state
- [ ] Baseline test coverage measurement
- [ ] Performance benchmark establishment
- [ ] Documentation of current behavior

#### Post-Phase Validation
- [ ] All tests pass
- [ ] No import errors
- [ ] Performance maintained or improved
- [ ] Documentation updated

#### Final Validation Checklist
- [ ] Zero Docker references in src/agents/claude_code/
- [ ] Test coverage >= 85%
- [ ] All workflows execute successfully
- [ ] Project rename completed
- [ ] Documentation reflects local-only architecture

### Rollback Strategy

#### Emergency Rollback Procedure
1. **Immediate**: Git revert to pre-cleanup commit
2. **Short-term**: Restore from backup branch
3. **Long-term**: Selective restoration of removed components

#### Rollback Triggers
- Test coverage drops below 80%
- Critical functionality breaks
- Performance degrades significantly
- Integration failures with other systems

### Success Metrics

#### Quantitative Metrics
- **Codebase Reduction**: Target 1,000+ lines removed
- **Test Execution Speed**: Target 20%+ improvement
- **Test Coverage**: Maintain 85%+ coverage
- **Build Time**: Maintain or improve current times

#### Qualitative Metrics
- **Code Clarity**: Simplified architecture
- **Maintainability**: Reduced complexity
- **Developer Experience**: Easier setup and debugging
- **Documentation Quality**: Clear local-only focus

### Timeline Summary

| Phase | Duration | Risk | Dependencies |
|-------|----------|------|--------------|
| Phase 1: Deadcode Removal | 1 day | LOW | None |
| Phase 2: Architecture Simplification | 2 days | MEDIUM | Phase 1 complete |
| Phase 3: Test Suite Consolidation | 3 days | MEDIUM-HIGH | Phase 2 complete |
| Phase 4: Project Rename | 1 day | LOW | Phases 1-3 complete |
| **Total** | **7 days** | **MEDIUM** | Sequential execution |

### Implementation Team Handoff

#### For IMPLEMENT Workflow
1. **Architecture Documents**: Complete design specifications
2. **Execution Plan**: Step-by-step implementation guide
3. **Validation Criteria**: Clear success metrics
4. **Risk Mitigation**: Comprehensive rollback procedures

#### Critical Implementation Notes
- Execute phases sequentially with validation between each
- Maintain test coverage throughout the process
- Document any deviations from the plan
- Escalate any breaking changes for human approval

This detailed execution plan provides the foundation for successfully transforming Claude Code to a local-only architecture while maintaining functionality and improving maintainability.