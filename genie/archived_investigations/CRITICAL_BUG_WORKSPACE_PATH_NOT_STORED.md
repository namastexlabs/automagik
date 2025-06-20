# CRITICAL BUG: Workspace Path Not Stored in Database

## Summary
The workspace path is created during workflow execution but is NEVER stored in the workflow_runs table, causing the status reporting endpoint to show "No workspace path found".

## Root Cause Analysis

### 1. Workspace Creation (agent.py:836-842)
```python
workspace_path = await self.executor.environment_manager.create_workspace(
    run_id=run_id,
    workflow_name=workflow_name,
    persistent=request.persistent,
    git_branch=request.git_branch
)
logger.info(f"Created workspace for run {run_id}: {workspace_path}")
```
The workspace is created and logged, but NOT stored in the database.

### 2. Database Record Creation (claude_code_routes.py:359-378)
The workflow_run record is created BEFORE workspace creation with workspace_path=None:
```python
workflow_run_data = WorkflowRunCreate(
    run_id=run_id,
    # ... other fields ...
    workspace_persistent=persistent,
    # workspace_path is NOT set here!
)
```

### 3. Status Endpoint Query
The status endpoint queries the database and finds workspace_path=NULL, leading to:
```
No workspace path found for run 36b15d0e-7238-445b-afa2-14959e006361
```

## Impact
- Status endpoint cannot report workspace location
- Workspace cleanup service cannot find associated workspaces
- Git operations may fail due to missing workspace context
- Recovery service cannot properly retry workflows

## Fix Required
After workspace creation in agent.py, immediately update the workflow_run record:

```python
# After line 842 in agent.py
if workspace_path:
    from ...db.repository.workflow_run import update_workflow_run_by_run_id
    from ...db.models import WorkflowRunUpdate
    
    update_data = WorkflowRunUpdate(
        workspace_path=str(workspace_path),
        updated_at=datetime.utcnow()
    )
    update_workflow_run_by_run_id(run_id, update_data)
    logger.info(f"Updated workflow run {run_id} with workspace path: {workspace_path}")
```

## Verification
1. The logs show: "Created workspace for run 36b15d0e-7238-445b-afa2-14959e006361: /home/namastex/workspace/am-agents-labs/worktrees/builder_persistent"
2. Database query shows: workspace_path=NULL
3. This confirms the workspace is created but not stored

## Priority: P0 - CRITICAL
This breaks core functionality of the workflow system.