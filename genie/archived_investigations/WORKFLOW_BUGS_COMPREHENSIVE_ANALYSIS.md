# Comprehensive Analysis: Workflow Execution Bugs

## Executive Summary
The workflow execution system has multiple critical bugs that prevent proper workspace tracking, causing failures in status reporting, auto-commit, and cleanup operations.

## Bug #1: Workspace Path Not Stored in Database

### Problem
When a workspace is created during workflow execution, the path is never stored in the workflow_runs table.

### Evidence
- Log shows: `Created workspace for run 36b15d0e-7238-445b-afa2-14959e006361: /home/namastex/workspace/am-agents-labs/worktrees/builder_persistent`
- Database query shows: `workspace_path=NULL`

### Location
- `src/agents/claude_code/agent.py:842` - Workspace created but not stored
- `src/api/routes/claude_code_routes.py:359-378` - workflow_run created without workspace_path

### Fix
```python
# In agent.py after line 842
if workspace_path:
    update_data = WorkflowRunUpdate(
        workspace_path=str(workspace_path),
        updated_at=datetime.utcnow()
    )
    update_workflow_run_by_run_id(run_id, update_data)
```

## Bug #2: Workspace Key Mismatch

### Problem
Workspaces are stored using `run_id` as key but retrieved using `claude_session_id`.

### Evidence
- Storage: `self.active_workspaces[run_id] = worktree_path`
- Retrieval: `workspace_path = active_workspaces.get(claude_session_id)`
- Log shows: `Active workspaces: ['36b15d0e-7238-445b-afa2-14959e006361']` (run_id)
- Log shows: `Workspace path for claude_session_id=291ad7c0-6b88-4f8a-a549-28c611755c5c: None`

### Location
- `src/agents/claude_code/cli_environment.py:120,155` - Storage with run_id
- `src/agents/claude_code/agent.py:965,1021` - Retrieval with claude_session_id

### Fix Options
1. Store with both keys
2. Always use run_id for retrieval
3. Maintain a mapping between run_id and claude_session_id

## Bug #3: Session ID Confusion

### Problem
Multiple session IDs exist causing confusion:
- `session_id` (database session): `915c149c-8fa8-445e-b332-ff31d40954e4`
- `claude_session_id` (Claude's internal): `291ad7c0-6b88-4f8a-a549-28c611755c5c`
- `run_id` (workflow run): `36b15d0e-7238-445b-afa2-14959e006361`

### Impact
- Workspace lookups fail
- Session continuity broken
- Status reporting confused

## Bug #4: Race Condition in Status Updates

### Problem
The workflow_run record is created with `status="pending"` but may not be updated to `status="running"` before status queries.

### Evidence
- Workflow shows as running in logs but database may show pending
- Status endpoint relies on database state

### Location
- `src/api/routes/claude_code_routes.py:389-407` - Background task updates

## Impact Summary

1. **Status Endpoint**: Cannot report workspace location
2. **Auto-commit**: Fails because workspace cannot be found
3. **Cleanup Service**: Cannot associate workspaces with runs
4. **Recovery Service**: Cannot properly retry workflows
5. **Git Operations**: May fail due to missing workspace context

## Recommended Fix Priority

1. **P0**: Fix workspace path storage in database (Bug #1)
2. **P0**: Fix workspace key mismatch (Bug #2)
3. **P1**: Clarify session ID usage (Bug #3)
4. **P1**: Fix race conditions in status updates (Bug #4)

## Testing Required

1. Create a workflow and verify workspace_path is stored
2. Verify status endpoint shows correct workspace
3. Verify auto-commit can find workspace
4. Test session continuation with proper workspace recovery
5. Test cleanup service can find and clean workspaces

## Root Cause
The system was designed with multiple session/ID concepts but lacks proper mapping between them. The workspace management was added later and not fully integrated with the database tracking system.