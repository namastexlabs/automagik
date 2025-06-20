# 🚨 CRITICAL BUG SUMMARY & MANUAL FIX GUIDE

**Date**: 2025-06-20  
**Severity**: P0 - BLOCKING ALL WORKFLOWS

## 🔴 Current State: WORKFLOWS BROKEN

### Issue #1: Subprocess Python Environment (BLOCKING)
- **Problem**: Workflows fail with "Claude Code not found"
- **Cause**: Subprocess doesn't use virtual environment Python
- **Impact**: NO workflows can execute

### Issue #2: Workspace Path Never Saved
- **Problem**: workspace_path is always NULL in database
- **Cause**: Path created but never stored
- **Impact**: Git operations fail, monitoring broken

### Issue #3: Status Reporting Wrong
- **Problem**: All workflows show as failed
- **Cause**: Using phase instead of status
- **Impact**: 100% false negative monitoring

## 🛠️ MANUAL FIXES REQUIRED

### Fix #1: Subprocess Python (MOST URGENT)

**File**: `src/agents/claude_code/execution_isolator.py`
**Line**: ~262

**Current Code**:
```python
process = await asyncio.create_subprocess_exec(
    sys.executable,
    temp_script_path,
    ...
)
```

**Fixed Code**:
```python
# Use virtual environment Python explicitly
venv_python = Path(__file__).parent.parent.parent.parent / ".venv" / "bin" / "python"
if not venv_python.exists():
    venv_python = sys.executable

process = await asyncio.create_subprocess_exec(
    str(venv_python),
    temp_script_path,
    ...
)
```

### Fix #2: Save Workspace Path

**File**: `src/agents/claude_code/agent.py`
**Location**: After workspace creation (~line 370)

**Add this code after workspace is created**:
```python
# Update workflow run with workspace path
if self.workflow_run_repo and run_id:
    try:
        from src.db.models import WorkflowRunUpdate
        update_data = WorkflowRunUpdate(
            workspace_path=str(workspace_path)
        )
        self.workflow_run_repo.update_workflow_run(run_id, update_data)
        logger.info(f"Updated workflow run {run_id} with workspace path: {workspace_path}")
    except Exception as e:
        logger.error(f"Failed to update workspace path: {e}")
```

### Fix #3: Status Reporting

**File**: `src/api/routes/claude_code_routes.py`
**Location**: In the status endpoint (~line 580)

**Current Code**:
```python
"success": result.get("phase") == "completed"
```

**Fixed Code**:
```python
"success": workflow_run.status == "completed"
```

### Fix #4: Workspace Key Mismatch

**File**: `src/agents/claude_code/cli_environment.py`
**Location**: In get_workspace_path method

**Current Code**:
```python
# Looking up with claude_session_id
workspace_info = self.active_workspaces.get(claude_session_id)
```

**Fixed Code**:
```python
# First try run_id, then fall back to claude_session_id
workspace_info = self.active_workspaces.get(run_id)
if not workspace_info and claude_session_id:
    workspace_info = self.active_workspaces.get(claude_session_id)
```

## 🚀 Quick Fix Commands

```bash
# 1. Activate virtual environment
source .venv/bin/activate

# 2. Apply the fixes manually using your editor
# Edit the files listed above

# 3. Restart the service
make restart

# 4. Test with a simple workflow
curl -X POST http://localhost:28881/api/v1/workflows/claude-code/run/test \
  -H "X-API-Key: namastex888" \
  -H "Content-Type: application/json" \
  -d '{"message": "echo test successful"}'

# 5. Check logs
make logs n=50
```

## 📊 Validation Steps

After fixes:
1. Workflows should execute without "Claude Code not found" error
2. Database should show workspace_path values (not NULL)
3. Status API should show "success": true for completed workflows
4. Git auto-commit should work

## 🎯 Priority

1. **Fix subprocess Python** - Without this, nothing works
2. **Fix workspace path storage** - Enables git operations
3. **Fix status reporting** - Accurate monitoring
4. **Fix workspace retrieval** - Complete the chain

These are surgical fixes that will restore workflow functionality!