# CRITICAL BUG: Workspace Storage Key Mismatch

## Summary
Workspaces are stored in active_workspaces dictionary using `run_id` as the key, but retrieved using `claude_session_id`, causing workspace lookups to fail.

## Root Cause Analysis

### 1. Storage (cli_environment.py:120,155)
```python
# Workspace is stored with run_id as key
self.active_workspaces[run_id] = worktree_path
```

### 2. Retrieval (agent.py:965,1021)
```python
# But retrieved with claude_session_id as key
claude_session_id = result.get("session_id")
workspace_path = self.executor.environment_manager.active_workspaces.get(claude_session_id)
```

### 3. The Mismatch
- run_id: `36b15d0e-7238-445b-afa2-14959e006361`
- claude_session_id: `291ad7c0-6b88-4f8a-a549-28c611755c5c`
- These are DIFFERENT values!

## Impact
- Workspace path cannot be found for git operations
- Auto-commit fails silently
- Workspace cleanup cannot associate workspaces with runs
- Status endpoint shows incorrect workspace information

## Evidence from Logs
```
📝 AUTO-COMMIT: Active workspaces: ['36b15d0e-7238-445b-afa2-14959e006361']
📝 AUTO-COMMIT: Workspace path for run_id=36b15d0e-7238-445b-afa2-14959e006361, claude_session_id=291ad7c0-6b88-4f8a-a549-28c611755c5c: None
```
The workspace exists under run_id but lookup uses claude_session_id!

## Fix Options

### Option 1: Store with Both Keys
```python
# In cli_environment.py create_workspace()
self.active_workspaces[run_id] = worktree_path
# Also store with session_id if available
if hasattr(self, 'session_id') and self.session_id:
    self.active_workspaces[self.session_id] = worktree_path
```

### Option 2: Always Use run_id for Lookup
```python
# In agent.py
workspace_path = self.executor.environment_manager.active_workspaces.get(run_id)
```

### Option 3: Pass run_id to Environment Manager
Store the run_id → claude_session_id mapping and use it for lookups.

## Verification
The logs clearly show:
1. Workspace stored under key: `36b15d0e-7238-445b-afa2-14959e006361`
2. Lookup attempted with key: `291ad7c0-6b88-4f8a-a549-28c611755c5c`
3. Result: None (workspace not found)

## Priority: P0 - CRITICAL
This breaks workspace tracking and all dependent features.