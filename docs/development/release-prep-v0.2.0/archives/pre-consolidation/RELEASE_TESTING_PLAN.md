# Release Testing Plan - Version 0.2.0

## Overview
This document outlines the comprehensive testing strategy to ensure all tests pass and functions work correctly for the 0.2 release of the automagik-agents codebase.

## Current State Analysis

### Discovered Issues
1. **Test Infrastructure**: 897 total tests collected
2. **Primary Issue**: Test execution timeouts and environment inconsistencies
3. **Specific Failure**: Claude Code agent workspace path mismatch (`/home/namastex/claude-workspace` vs `/tmp/claude-workspace`)
4. **Runtime Environment**: Tests must use `uv run` for all Python command execution

### Test Categories
- **Unit Tests**: Agent initialization, models, utilities
- **Integration Tests**: Cross-agent functionality, database connections
- **Performance Tests**: MCP performance comparisons
- **Regression Tests**: Recently added test directory
- **IVT (Integration Verification Tests)**: End-to-end workflows

## Phase 1: Test Infrastructure Stabilization

### 1.1 Environment Standardization
- **Action**: Ensure all test execution uses `uv run pytest` 
- **Critical**: Update any scripts or documentation that reference direct `python` or `pytest` calls
- **Files to check**: CI/CD configs, scripts/, test runners

### 1.2 Path Configuration Issues
- **Issue**: Workspace base path inconsistency in Claude Code agent tests
- **Root Cause**: Test expects `/tmp/claude-workspace` but actual implementation uses `/home/namastex/claude-workspace`
- **Files affected**: `tests/agents/claude_code/test_agent.py:53`

### 1.3 Test Timeout Resolution
- **Issue**: Tests hanging during execution
- **Likely causes**: Database connections, async operations, external service calls
- **Action**: Implement test isolation and proper mocking

## Phase 2: Systematic Test Fixing

### 2.1 High-Priority Fixes (Critical for Release)
1. **Claude Code Agent Tests**
   - Fix workspace path expectations
   - Verify container manager initialization
   - Ensure executor factory mocking works correctly

2. **Database Connection Tests** 
   - Address SQLite connection initialization logs during test runs
   - Ensure proper test database isolation
   - Fix any connection pool issues

3. **MCP Integration Tests**
   - Resolve any MCP client connection issues
   - Verify migration system tests
   - Check safety trigger functionality

### 2.2 Medium-Priority Fixes
1. **Agent Parity Tests**
2. **Performance Comparison Tests**
3. **Airtable Integration Tests** (currently skipped)

### 2.3 Low-Priority Fixes  
1. **Documentation Tests**
2. **Utility Function Tests**

## Phase 3: Test Categories Validation

### 3.1 Unit Test Validation
```bash
uv run pytest tests/unit/ -v --tb=short
```

### 3.2 Integration Test Validation
```bash
uv run pytest tests/integration/ -v --tb=short
```

### 3.3 Agent-Specific Test Validation
```bash
uv run pytest tests/agents/ -v --tb=short
```

### 3.4 Performance Test Validation
```bash
uv run pytest tests/perf/ -v --tb=short
```

## Phase 4: Release Validation Framework

### 4.1 Pre-Release Test Suite
```bash
# Core functionality tests
uv run pytest tests/agents/claude_code/ tests/agents/pydanticai/ -v

# Database and MCP tests  
uv run pytest tests/db/ tests/mcp/ -v

# API and integration tests
uv run pytest tests/api/ tests/integration/ -v
```

### 4.2 Smoke Test Script
Create automated smoke test for critical paths:
- Agent initialization
- Database connectivity
- MCP functionality
- API endpoints

### 4.3 Performance Benchmarks
- Test execution time baselines
- Memory usage monitoring
- Resource utilization checks

## Phase 5: Continuous Validation

### 5.1 Test Execution Standards
- **All Python commands**: Must use `uv run`
- **Test isolation**: Each test should be independent
- **Mock external services**: No real API calls in unit tests
- **Database cleanup**: Proper teardown after each test

### 5.2 Quality Gates
- **Zero failing tests** in core functionality
- **No test timeouts** under normal conditions
- **Clean test output** with minimal warnings
- **Consistent test execution time**

## Implementation Priority Matrix

| Category | Priority | Estimated Effort | Risk Level |
|----------|----------|------------------|------------|
| Path Configuration Fix | P0 | 1-2 hours | Low |
| Test Timeout Resolution | P0 | 4-6 hours | Medium |
| Database Test Isolation | P1 | 2-4 hours | Medium |
| MCP Integration Tests | P1 | 3-5 hours | High |
| Performance Tests | P2 | 2-3 hours | Low |
| Regression Tests | P2 | 1-2 hours | Low |

## Success Criteria

### Must Have (P0)
- [ ] All critical path tests pass
- [ ] No test execution timeouts
- [ ] Claude Code agent tests work correctly
- [ ] Database tests run in isolation

### Should Have (P1)  
- [ ] Integration tests pass consistently
- [ ] MCP functionality tests work
- [ ] Performance tests provide baselines

### Nice to Have (P2)
- [ ] All skipped tests are addressed
- [ ] Full test coverage validation
- [ ] Automated smoke test suite

## Risk Mitigation

### High-Risk Areas
1. **MCP Integration**: Complex async operations, potential for hanging
2. **Database Migrations**: Data consistency and rollback scenarios
3. **Container Management**: Docker dependencies and cleanup

### Mitigation Strategies
1. **Comprehensive Mocking**: Isolate external dependencies
2. **Test Timeouts**: Set reasonable limits for all async operations
3. **Cleanup Procedures**: Ensure proper resource cleanup in all tests
4. **Gradual Rollout**: Fix tests incrementally by priority

## Next Steps

1. **Immediate**: Fix workspace path configuration issue
2. **Short-term**: Resolve test timeouts and stabilize test execution
3. **Medium-term**: Address all P0 and P1 test failures
4. **Long-term**: Implement continuous validation framework

## Notes

- This plan assumes `uv run` must be used for all Python execution
- Test count: 897 total tests identified
- Environment: Linux WSL2 with Python 3.12.3
- Framework: pytest with asyncio support