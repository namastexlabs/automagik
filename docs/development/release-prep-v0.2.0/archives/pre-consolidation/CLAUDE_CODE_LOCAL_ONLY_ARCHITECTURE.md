# Claude Code Local-Only Architecture Plan
## Epic: release-prep-v0.2.0

### Executive Summary

This document outlines the comprehensive architectural plan to transform Claude Code from a dual-mode (docker/local) system to a **local-only execution architecture** for the 0.2 release. This includes deadcode removal, test suite consolidation, and project renaming from "automagik-agents" to "automagik".

### Current State Analysis

#### Claude Code Components (As-Is)
```
src/agents/claude_code/
├── agent.py                 # Main agent with mode switching logic
├── cli_environment.py       # Environment management (local-focused)
├── cli_executor.py         # CLI execution logic (local-focused)
├── completion_tracker.py   # Completion tracking (mode-agnostic)
├── container.py            # 🗑️ DEADCODE - Docker container management
├── docker/                 # 🗑️ DEADCODE - Docker configuration
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── entrypoint.sh
├── docker_executor.py      # 🗑️ DEADCODE - Docker execution
├── executor_base.py        # Base class (keep for local)
├── executor_factory.py     # Factory with dual-mode logic
├── local_executor.py       # Local execution (primary implementation)
├── log_manager.py          # Logging (mode-agnostic)
├── models.py              # Data models (mode-agnostic)
├── raw_stream_processor.py # Stream processing (mode-agnostic)
├── repository_utils.py     # Repository utilities (local-focused)
└── workflows/             # Workflow definitions (local-only)
```

#### Test Suite Components (As-Is)
```
tests/agents/claude_code/
├── conftest.py             # Test configuration
├── test_agent.py          # Agent tests (mixed mode concerns)
├── test_cli_integration.py # CLI integration tests
├── test_container.py       # 🗑️ DEADCODE - Container tests
├── test_edge_cases.py     # Edge case tests
├── test_executor.py       # 🗑️ DEADCODE - Mixed executor tests
├── test_fixes.py          # Fix validation tests
├── test_integration.py    # Integration tests
├── test_models.py         # Model tests
└── test_performance.py    # Performance tests
```

### Architecture Decisions

#### Decision 1: Local-Only Execution Model
**Rationale**: Docker/container mode is incomplete and adds complexity without immediate value
**Impact**: Simplified architecture, faster development, reduced maintenance overhead
**Implementation**: Remove all Docker-related code and simplify to local execution only

#### Decision 2: Simplified Executor Architecture
**Before**: Factory pattern with mode switching
```python
# Current complex factory
ExecutorFactory.create_executor(mode="docker"|"local")
```

**After**: Direct local executor instantiation
```python
# Simplified architecture
LocalExecutor(workspace_base, cleanup_on_complete)
```

#### Decision 3: Test Suite Consolidation
**Approach**: Remove Docker tests, consolidate duplicated local tests, focus on actual functionality
**Benefit**: Faster test execution, clearer test intent, easier maintenance

#### Decision 4: Project Rename Integration
**Change**: "automagik-agents" → "automagik"
**Scope**: pyproject.toml, documentation, imports, package references

### Deadcode Identification

#### High-Confidence Deadcode (Immediate Removal)
```
src/agents/claude_code/
├── container.py                    # Docker container management
├── docker_executor.py             # Docker execution implementation
├── docker/                        # Entire Docker directory
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── entrypoint.sh

tests/agents/claude_code/
├── test_container.py              # Container management tests
└── test_executor.py               # Mixed executor tests (Docker parts)
```

#### Refactor Required (Mode Removal)
```
src/agents/claude_code/
├── agent.py                       # Remove mode switching logic
├── executor_factory.py           # Simplify to local-only
└── executor_base.py              # Simplify interface

tests/agents/claude_code/
├── test_agent.py                 # Remove Docker test cases
├── test_integration.py           # Remove Docker integration tests
└── test_performance.py          # Focus on local performance only
```

### Implementation Roadmap

#### Phase 1: Deadcode Removal (Immediate)
**Deliverables**:
1. Remove Docker-specific files
2. Remove Docker-specific test files
3. Update .gitignore to prevent future Docker artifacts

**Files to Delete**:
```bash
rm -rf src/agents/claude_code/docker/
rm src/agents/claude_code/container.py
rm src/agents/claude_code/docker_executor.py
rm tests/agents/claude_code/test_container.py
```

#### Phase 2: Architecture Simplification
**Deliverables**:
1. Simplify agent.py to local-only
2. Replace ExecutorFactory with direct LocalExecutor instantiation
3. Remove executor_base.py if no longer needed
4. Update environment variable handling

**Key Changes**:
- Remove `CLAUDE_CODE_MODE` environment variable
- Simplify executor initialization
- Remove container_manager dependencies

#### Phase 3: Test Suite Consolidation
**Deliverables**:
1. Audit all test files for Docker references
2. Consolidate duplicate test cases
3. Ensure comprehensive local execution coverage
4. Update test documentation

**Test Cleanup Strategy**:
- Remove Docker-specific test cases from all files
- Consolidate overlapping local tests
- Ensure all local execution paths are tested
- Add missing edge case coverage for local-only mode

#### Phase 4: Project Rename Implementation
**Deliverables**:
1. Update pyproject.toml package name
2. Update README and documentation
3. Update import statements if needed
4. Update CI/CD configurations

**Rename Scope**:
```toml
# pyproject.toml changes
[project]
name = "automagik"  # was "automagik-agents"
description = "Automagik AI agent framework"  # updated
```

### Breaking Changes Assessment

#### API Breaking Changes: NONE
- Local execution API remains unchanged
- Environment variables for local mode unchanged
- Workflow configurations unchanged

#### Configuration Breaking Changes: MINIMAL
- `CLAUDE_CODE_MODE` environment variable becomes unused (not removed for compatibility)
- All local mode configurations remain functional

#### Test Breaking Changes: EXPECTED
- Docker-related tests will be removed
- Some test utilities may need updates
- Test execution should be faster and more reliable

### Risk Assessment

#### Low Risk: Core Functionality
- Local execution is well-tested and stable
- Workflow system is independent of execution mode
- Configuration system is mostly local-focused

#### Medium Risk: Test Coverage
- Removing Docker tests may reduce overall coverage percentage
- Need to ensure local edge cases are well covered
- Integration tests need validation

#### High Risk: Hidden Dependencies
- Some components may have unexpected Docker dependencies
- Third-party integrations may assume Docker availability
- CI/CD pipelines may reference Docker components

### Success Criteria

#### Functional Requirements
1. All existing local-mode functionality preserved
2. No regression in workflow execution
3. Simplified codebase with clear local-only architecture
4. All tests pass with local execution only

#### Non-Functional Requirements
1. Reduced codebase size by removing deadcode
2. Faster test execution (no Docker overhead)
3. Simplified development setup
4. Clear architectural boundaries

#### Quality Gates
1. Test coverage maintained at current levels
2. No increase in cyclomatic complexity
3. Documentation updated to reflect local-only architecture
4. Clean code quality metrics

### Implementation Constraints

#### Technical Constraints
- Must maintain backward compatibility for local mode
- Cannot break existing workflow configurations
- Must preserve all local execution features

#### Business Constraints
- 0.2 release timeline requirements
- Coordination with other release-prep tasks
- Minimal disruption to development workflow

#### Resource Constraints
- Implementation must be achievable within sprint capacity
- Testing must be thorough but efficient
- Documentation updates must be comprehensive

### Detailed Component Analysis

#### agent.py Simplification
**Current Complexity**: Mode switching logic, container manager creation
**Target State**: Direct local executor initialization
**Changes Required**:
```python
# Remove
self.execution_mode = os.environ.get("CLAUDE_CODE_MODE", "local").lower()
self._create_container_manager()

# Simplify to
self.executor = LocalExecutor(
    workspace_base=os.environ.get("CLAUDE_LOCAL_WORKSPACE", "/tmp/claude-workspace"),
    cleanup_on_complete=os.environ.get("CLAUDE_LOCAL_CLEANUP", "true").lower() == "true"
)
```

#### executor_factory.py Evolution
**Current Role**: Factory pattern for mode selection
**Future Role**: Utility functions for local executor configuration
**Alternative**: Complete removal in favor of direct instantiation

#### Test Suite Transformation
**Current Issues**: Mixed concerns, Docker dependencies, redundant test cases
**Target State**: Focused local execution tests, clear test boundaries
**Consolidation Opportunities**:
- Merge similar local execution test cases
- Remove Docker-specific mocking
- Simplify test setup/teardown

### Migration Strategy

#### Backward Compatibility
- Keep unused environment variables for grace period
- Maintain API signatures where possible
- Provide clear migration guide for any changes

#### Rollback Plan
- Tag current state before changes
- Maintain Docker files in separate branch temporarily
- Document rollback procedure

#### Validation Approach
- Comprehensive test suite execution
- Performance benchmarking
- Integration testing with existing workflows

### Documentation Updates Required

#### Architecture Documentation
- Update system architecture diagrams
- Revise component interaction diagrams
- Document simplified execution flow

#### Developer Documentation
- Update setup instructions (remove Docker requirements)
- Revise troubleshooting guides
- Update contributing guidelines

#### User Documentation
- Update configuration documentation
- Revise workflow execution guides
- Update environment variable documentation

### Dependencies and Integration Points

#### Internal Dependencies
- Memory system integration (unchanged)
- Workflow system integration (unchanged)
- Logging system integration (unchanged)

#### External Dependencies
- Claude CLI tool (unchanged)
- Git operations (unchanged)
- File system operations (unchanged)

#### Integration Testing Requirements
- Workflow execution end-to-end
- Memory system integration
- Configuration system validation

### Quality Assurance Strategy

#### Code Quality Measures
- Static analysis with existing tools
- Code coverage measurement and maintenance
- Complexity analysis and reduction verification

#### Testing Strategy
- Unit test coverage for all modified components
- Integration test validation
- Performance regression testing

#### Review Process
- Architectural review of simplified design
- Code review of all changes
- Testing review of consolidated test suite

This architectural plan provides a comprehensive roadmap for transforming Claude Code to a local-only execution model while maintaining functionality and improving maintainability for the 0.2 release.