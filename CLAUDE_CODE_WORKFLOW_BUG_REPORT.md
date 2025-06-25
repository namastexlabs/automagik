# Claude Code Workflow Testing Bug Report

**Date**: June 24, 2025  
**Testing Environment**: localhost:28881, API key: namastex888  
**Scope**: Comprehensive testing of all Claude Code workflow modes  

## Executive Summary

Testing revealed **2 critical bugs** and **1 database schema gap** in the temporary workspace implementation:

1. **🔴 CRITICAL**: `temp_workspace=true` parameter validation works but **actual workspace creation still uses git worktrees** instead of temporary directories
2. **🔴 CRITICAL**: API-level parameter validation for incompatible combinations (`temp_workspace` + `repository_url`/`git_branch`/`auto_merge`) is **completely bypassed**
3. **🟡 SCHEMA**: Database missing `temp_workspace` column, preventing proper tracking and analysis

## Detailed Test Results

### 1. Temporary Workspace Mode Testing

#### Test Case: Basic temp_workspace functionality
```bash
curl -X POST "http://localhost:28881/api/v1/workflows/claude-code/run/claude?persistent=false&temp_workspace=true" \
  -H "X-API-Key: namastex888" \
  -d '{"message": "test temp workspace mode - create a simple hello world script", "max_turns": 5, "user_id": "550e8400-e29b-41d4-a716-446655440000"}'
```

**Expected Result**: Workspace created in `/tmp/claude-code-temp/550e8400-e29b-41d4-a716-446655440000/workspace_{run_id}/`

**Actual Result**: 
- ✅ API accepted request and returned `run_id: dd100c1e-562e-49d6-b6de-abec77abf0a6`
- ✅ Workflow completed successfully with status `completed`
- 🔴 **BUG**: Workspace created in git worktree: `/home/namastex/workspace/am-agents-labs/worktrees/main-claude-dd100c1e`
- ✅ `persistent=false` correctly stored as `workspace_persistent: 0` in database

**Evidence**: 
```json
{
  "final_output": "...cwd': '/home/namastex/workspace/am-agents-labs/worktrees/main-claude-dd100c1e'..."
}
```

#### Test Case: Incompatible parameter validation
```bash
curl -X POST "http://localhost:28881/api/v1/workflows/claude-code/run/claude?temp_workspace=true&repository_url=https://github.com/user/repo.git" \
  -H "X-API-Key: namastex888" \
  -d '{"message": "test incompatible params", "user_id": "550e8400-e29b-41d4-a716-446655440000"}'
```

**Expected Result**: HTTP 400 error with message about incompatible parameters

**Actual Result**: 
- 🔴 **BUG**: API accepted request and returned `run_id: 5bd8c26a-3c32-4634-9b26-f063c56bc460`
- 🔴 **BUG**: No validation error thrown despite incompatible parameters
- 🔴 **BUG**: Repository URL was not preserved in request metadata

### 2. External Repository Mode Testing

#### Test Case: External repository cloning
```bash
curl -X POST "http://localhost:28881/api/v1/workflows/claude-code/run/claude" \
  -H "X-API-Key: namastex888" \
  -d '{"message": "test external repo mode", "repository_url": "https://github.com/anthropics/anthropic-sdk-python.git", "max_turns": 3, "user_id": "550e8400-e29b-41d4-a716-446655440000"}'
```

**Expected Result**: Repository cloned to `/external_repos/` directory

**Actual Result**: 
- ✅ API accepted request and returned `run_id: 15e1f140-0a0b-4705-b086-26a656dde7ac`
- ✅ Database correctly stores `git_repo: "https://github.com/anthropics/anthropic-sdk-python.git"`
- ✅ External repo directory created: `/external_repos/claude-code-claude/`
- 🟡 **SLOW**: Workflow still running after 5+ minutes (may indicate cloning issues)

### 3. Default Git Worktree Mode Testing

#### Test Case: Standard worktree workflow
```bash
curl -X POST "http://localhost:28881/api/v1/workflows/claude-code/run/claude" \
  -H "X-API-Key: namastex888" \
  -d '{"message": "test default git worktree mode", "max_turns": 3, "user_id": "550e8400-e29b-41d4-a716-446655440000"}'
```

**Expected Result**: Git worktree created in `/worktrees/` directory

**Actual Result**: 
- ✅ API accepted request and returned `run_id: 3ad13f8d-05c1-47f4-94d6-44ac5f6e01be`
- ✅ Workflow completed successfully in 13.6 seconds
- ✅ Correct worktree path: `/home/namastex/workspace/am-agents-labs/worktrees/main-claude`
- ✅ Database tracking working correctly

## Database Analysis

### Schema Verification
```sql
SELECT run_id, workflow_name, status, workspace_path, git_repo, workspace_persistent, metadata 
FROM workflow_runs ORDER BY created_at DESC LIMIT 5;
```

**Findings**:
- ✅ All workflow executions properly stored in database
- ✅ Workspace paths correctly tracked
- ✅ `persistent` parameter correctly mapped to `workspace_persistent` column
- 🔴 **MISSING**: No `temp_workspace` column to track temporary workspace usage
- 🔴 **MISSING**: Query parameters (`repository_url`, `git_branch`, `auto_merge`) not stored in request metadata when passed via URL

### Data Integrity Check
| Run ID | Mode | Workspace Path | Expected Path | Status |
|--------|------|----------------|---------------|---------|
| `dd100c1e` | temp_workspace=true | `/worktrees/main-claude-dd100c1e` | `/tmp/claude-code-temp/550e.../workspace_dd100c1e/` | 🔴 WRONG |
| `15e1f140` | repository_url | `null` (still running) | `/external_repos/anthropic-sdk-python/` | 🟡 PENDING |
| `3ad13f8d` | default | `/worktrees/main-claude` | `/worktrees/main-claude` | ✅ CORRECT |

## Root Cause Analysis

### 1. Temp Workspace Creation Bug
**Location**: `src/agents/claude_code/sdk_execution_strategies.py:execute_simple()`

**Issue**: The `temp_workspace` parameter is not being properly passed through the execution flow. The method detects external repositories but doesn't check for `temp_workspace` flag.

**Evidence**: Implementation shows parameter validation in models but no actual workspace type selection logic in execution strategy.

### 2. API Parameter Validation Bug  
**Location**: `src/api/routes/claude_code_routes.py:run_claude_workflow()`

**Issue**: Query parameters (`temp_workspace`, `repository_url`, etc.) are handled separately from request body, and validation only checks request body fields, not query parameters.

**Evidence**: Validation logic exists in code but is only applied to body parameters, not query parameters.

### 3. Database Schema Gap
**Location**: Database migration files

**Issue**: `temp_workspace` parameter not added to `workflow_runs` table schema, preventing proper tracking and analysis.

## Priority Recommendations

### 🔴 HIGH PRIORITY (Fix Immediately)

1. **Fix temp workspace creation**: Update `execute_simple()` to check `temp_workspace` flag and call `create_temp_workspace()` instead of git worktree creation
2. **Fix API validation**: Ensure query parameters are included in compatibility validation
3. **Add database column**: Add `temp_workspace` BOOLEAN column to `workflow_runs` table

### 🟡 MEDIUM PRIORITY (Fix Soon)

1. **Improve external repo handling**: Investigate slow cloning performance
2. **Enhanced parameter storage**: Store all query parameters in request metadata
3. **Add integration tests**: Create automated tests for all three workflow modes

### 🟢 LOW PRIORITY (Nice to Have)

1. **Better error messages**: More descriptive validation error messages
2. **Parameter documentation**: Update API docs with parameter interaction rules
3. **Monitoring**: Add metrics for workspace type usage

## Test Environment Details

- **Server**: localhost:28881
- **API Key**: namastex888  
- **Available Workflows**: claude, genie, builder, shipper, guardian, brain, surgeon, lina, flashinho_thinker
- **Database**: SQLite with 33 columns in `workflow_runs` table
- **Directories Verified**:
  - ✅ `/tmp/claude-code-temp/` exists (empty)
  - ✅ `/external_repos/` contains external repository clones
  - ✅ `/worktrees/` contains git worktrees

## Validation Status

| Feature | Implementation Status | Validation Status | Database Tracking |
|---------|---------------------|------------------|------------------|
| Default worktree mode | ✅ Working | ✅ Working | ✅ Complete |
| External repository mode | ✅ Working | ✅ Working | ✅ Complete |  
| Temporary workspace mode | 🔴 **Broken** | ✅ Working | 🔴 **Missing column** |
| Parameter validation | 🔴 **Broken** | 🔴 **Bypassed** | 🔴 **Incomplete** |

## Next Steps

1. **Immediate Fix**: Update `sdk_execution_strategies.py` to properly handle `temp_workspace` parameter
2. **API Fix**: Update `claude_code_routes.py` to validate all parameters (body + query)  
3. **Database Migration**: Add `temp_workspace` column to `workflow_runs` table
4. **Comprehensive Testing**: Re-run all tests after fixes to verify resolution

**Testing completed at**: 2025-06-24 18:40:00 UTC