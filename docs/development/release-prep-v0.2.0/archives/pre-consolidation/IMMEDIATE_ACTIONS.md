# Immediate Actions for 0.2 Release

## Critical Fixes Needed Now

### 1. Fix Claude Code Agent Test Path Issue
**File**: `tests/agents/claude_code/test_agent.py:53`
**Issue**: Expected workspace path `/tmp/claude-workspace` but actual is `/home/namastex/claude-workspace`
**Fix**: Update test expectation to match actual implementation

### 2. Standardize uv run Usage  
**Issue**: All Python execution must use `uv run`
**Action**: Audit and update all scripts, documentation, and workflows

### 3. Resolve Test Timeouts
**Issue**: Tests hanging during execution, likely due to database initialization
**Action**: Implement proper test isolation and mocking

## Quick Fix Commands

### Fix the immediate test failure:
```bash
# Test the current failure
uv run pytest tests/agents/claude_code/test_agent.py::TestClaudeCodeAgentInitialization::test_agent_initialization -v

# After fixing the test, verify it passes
uv run pytest tests/agents/claude_code/test_agent.py -v
```

### Run test categories separately to identify issues:
```bash
# Test each category with timeout protection
uv run pytest tests/unit/ -v --tb=short --timeout=30
uv run pytest tests/agents/claude_code/ -v --tb=short --timeout=30  
uv run pytest tests/db/ -v --tb=short --timeout=30
```

### Check for uv run compliance:
```bash
# Search for non-uv python calls in scripts
grep -r "python " scripts/ | grep -v "uv run"
grep -r "pytest" scripts/ | grep -v "uv run"
```

## Implementation Order

1. **FIRST**: Fix workspace path test expectation
2. **SECOND**: Audit scripts for uv run compliance  
3. **THIRD**: Add test timeouts and isolation
4. **FOURTH**: Run full test suite validation

## Expected Timeline

- **Immediate (30 minutes)**: Fix workspace path test
- **Short-term (2 hours)**: Address uv run compliance
- **Medium-term (4 hours)**: Resolve timeout issues
- **Validation (2 hours)**: Full test suite run

## Success Metrics

- [ ] Claude Code agent test passes
- [ ] No test timeouts under 30 seconds
- [ ] All scripts use uv run consistently
- [ ] Test suite completes successfully

This addresses the most critical blockers for the 0.2 release testing.