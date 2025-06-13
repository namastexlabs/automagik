# Comprehensive Cleanup Plan for 0.2 Release

## Critical Issues Discovered

### 1. Massive Code Duplication (6GB!)
**Issue**: Recursive nested directories in claude_code workflows
- `src/agents/claude_code/workflows/test/workflow/` (3.9GB)
- `src/agents/claude_code/workflows/architect/workflow/` (2.0GB)
- **Total waste**: ~6GB of duplicated source code

**Root Cause**: Workflow system appears to have recursively copied entire codebase

### 2. Environment Configuration Issues
**Fixed**: Workspace path correctly configured in `.env`
- `CLAUDE_LOCAL_WORKSPACE=/home/namastex/claude-workspace` (line 97)
- Test expectations need to use this value, not hardcoded `/tmp/claude-workspace`

### 3. Database Configuration Change
**Issue**: Switched from PostgreSQL to SQLite
- `.env` line 22: `DATABASE_TYPE=sqlite` 
- `SQLITE_DATABASE_PATH=./data/automagik_agents.db` (line 25)
- Many tests likely written for PostgreSQL patterns

### 4. Legacy Code (_old.py files)
**Found**: 9 agent_old.py files that should be removed:
- `src/agents/pydanticai/*/agent_old.py` across multiple agents
- Various connection_old.py and related files

## Phase 1: Emergency Cleanup (CRITICAL)

### 1.1 Remove Massive Duplicate Directories
```bash
# DANGER: These are 6GB of duplicates - remove carefully
rm -rf src/agents/claude_code/workflows/test/workflow/am-agents-labs/
rm -rf src/agents/claude_code/workflows/architect/workflow/am-agents-labs/

# Verify workflows still work after cleanup
ls -la src/agents/claude_code/workflows/*/
```

### 1.2 Clean Up Recursive .env Files
```bash
# Remove all nested .env files (these are duplicates)
find src/agents/claude_code/workflows/ -name ".env" -not -path "*/workflow/am-agents-labs/*" -delete

# Keep only root .env file
```

### 1.3 Remove Legacy _old.py Files
```bash
# Remove all agent_old.py files
find src/ -name "*_old.py" -not -path "*/workflow/*" -delete

# Specifically:
rm src/agents/pydanticai/*/agent_old.py
```

## Phase 2: Database Migration Compatibility

### 2.1 SQLite Test Compatibility Review
**Files to check**:
- All tests in `tests/db/` - many assume PostgreSQL
- Connection pool tests - SQLite has different behavior
- Migration tests - schema differences
- Performance tests - different optimization patterns

### 2.2 Environment-based Test Configuration
**Action**: Update tests to read database config from environment
```python
# Instead of hardcoded PostgreSQL assumptions
database_type = os.getenv('DATABASE_TYPE', 'sqlite')
```

### 2.3 Test Database Isolation
**Issue**: SQLite file-based DB needs different cleanup patterns
- PostgreSQL: DROP DATABASE
- SQLite: DELETE file or IN-MEMORY database

## Phase 3: Test Environment Standardization

### 3.1 Fix Workspace Path Tests
**File**: `tests/agents/claude_code/test_agent.py:53`
**Change**: 
```python
# From:
workspace_base="/tmp/claude-workspace"
# To: 
workspace_base=os.getenv('CLAUDE_LOCAL_WORKSPACE', '/tmp/claude-workspace')
```

### 3.2 Database Test Configuration
**Create**: Test configuration that works with both SQLite and PostgreSQL
```python
# Test helper for database cleanup
def cleanup_test_database():
    if os.getenv('DATABASE_TYPE') == 'sqlite':
        db_path = os.getenv('SQLITE_DATABASE_PATH')
        if os.path.exists(db_path):
            os.remove(db_path)
    else:
        # PostgreSQL cleanup
        pass
```

### 3.3 Environment Consistency
**Standardize**: All tests must use the same environment loading
- Check `.env` loading order
- Ensure test overrides work correctly
- Validate uv run compatibility

## Phase 4: Dead Code Removal

### 4.1 MCP Refactor Cleanup
**Files to review**:
- `tests/mcp/` - check for obsolete test patterns
- `src/mcp/` - identify deprecated interfaces
- Migration-related tests that may no longer apply

### 4.2 Obsolete Test Categories
**Review**:
- Tests that assume PostgreSQL-only features
- Tests for removed MCP functionality
- Container tests that may not work in current env

### 4.3 Import and Dependency Cleanup
**Action**: Remove imports of deleted modules
```bash
# Find imports of removed files
uv run python -c "import ast; import os; [print(f) for f in os.listdir('src/') if f.endswith('.py')]"
```

## Phase 5: Test Execution Fixes

### 5.1 Timeout Issues Resolution
**Root Cause**: Database initialization taking too long
- SQLite file creation and locking
- Connection pool setup for file-based DB
- Transaction isolation differences

### 5.2 Test Isolation Improvements
**Strategy**:
- Use in-memory SQLite for tests: `":memory:"`
- Proper teardown for file-based databases  
- Mock external services more consistently

### 5.3 Parallel Test Execution
**Issue**: SQLite file locking conflicts in parallel tests
**Solution**: Each test gets unique database file or use in-memory

## Immediate Actions (Next 30 minutes)

### Priority 1: Disk Space Recovery
1. **Remove 6GB of duplicates**: 
   ```bash
   rm -rf src/agents/claude_code/workflows/*/workflow/am-agents-labs/
   ```

2. **Remove legacy files**:
   ```bash
   find src/ -name "*_old.py" -not -path "*/workflow/*" -delete
   ```

### Priority 2: Fix Immediate Test Failure
1. **Update workspace path test**:
   - Edit `tests/agents/claude_code/test_agent.py:53`
   - Use environment variable instead of hardcoded path

### Priority 3: Database Test Configuration
1. **Check SQLite test compatibility**:
   ```bash
   uv run pytest tests/db/ -v --tb=short -x
   ```

## Success Metrics

### Immediate (30 minutes)
- [ ] Disk space reduced by 6GB
- [ ] Legacy _old.py files removed  
- [ ] Workspace path test passes

### Short-term (2 hours)  
- [ ] All database tests work with SQLite
- [ ] Test execution under 30 seconds per category
- [ ] No test timeouts

### Medium-term (4 hours)
- [ ] All 897 tests categorized and working
- [ ] Dead code completely removed
- [ ] Clean test output with minimal warnings

## Risk Assessment

### High Risk
- **Removing 6GB directories**: Could break workflow system if they're actually needed
- **Database changes**: Many tests might assume PostgreSQL behavior
- **Environment differences**: SQLite vs PostgreSQL feature gaps

### Mitigation
- **Backup before deletion**: Git stash changes before major deletions
- **Incremental testing**: Test each phase separately
- **Environment variables**: Make tests adaptable to both database types

## File Cleanup Checklist

### Confirmed Dead Code
- [ ] `src/agents/claude_code/workflows/*/workflow/am-agents-labs/` (6GB duplicates)
- [ ] `src/agents/pydanticai/*/agent_old.py` (9 files)
- [ ] Nested `.env` files in workflows (100+ duplicates)

### Needs Review
- [ ] `tests/db/test_mcp_*` - may have obsolete MCP patterns
- [ ] `tests/perf/test_mcp_performance_comparison.py` - check if still relevant
- [ ] Migration-related tests - validate against new MCP architecture

### Environment Dependencies
- [ ] All Python execution uses `uv run`
- [ ] Database type correctly detected from `.env`
- [ ] Workspace paths read from environment
- [ ] Test isolation works with SQLite

This cleanup will dramatically reduce codebase size, fix immediate test failures, and prepare for a clean 0.2 release.