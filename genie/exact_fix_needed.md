# 🔧 EXACT FIX NEEDED - Workspace Creation Bug

## Location
**File**: `src/agents/claude_code/agent.py`
**Line**: Around 833-843

## Current Code (BROKEN)
```python
# Line 833-843
# Execute the workflow - use standard execution to avoid SDK TaskGroup issues
# The SDK executor can extract data from the result without streaming complications
result = await self.executor.execute_claude_task(
    request=request,
    agent_context={
        "workflow_name": workflow_name,
        "session_id": session_id,
        "run_id": run_id,  # Ensure run_id is always present for logging
        "db_id": self.db_id
    }
)
```

## Fixed Code (NEEDED)
```python
# BEFORE line 833, ADD:
# Create workspace for this workflow run
workspace_path = None
if hasattr(self.executor, 'environment_manager') and self.executor.environment_manager:
    workspace_path = await self.executor.environment_manager.create_workspace(
        run_id=run_id,
        workflow_name=workflow_name,
        persistent=request.persistent,  # Use the persistent flag from request
        git_branch=request.git_branch
    )
    logger.info(f"Created workspace for run {run_id}: {workspace_path}")

# THEN modify the agent_context to include workspace:
result = await self.executor.execute_claude_task(
    request=request,
    agent_context={
        "workflow_name": workflow_name,
        "session_id": session_id,
        "run_id": run_id,
        "db_id": self.db_id,
        "workspace": str(workspace_path) if workspace_path else "."  # ADD THIS LINE
    }
)
```

## Why This Fixes It

1. **Creates the workspace** before SDK execution
2. **Passes the workspace path** to the SDK executor
3. **Tracks the workspace** in active_workspaces with run_id
4. **SDK executor uses the workspace** instead of default "."

## Additional Consideration

The workspace lookup issue (using claude_session_id vs run_id) also needs fixing, but this is the primary fix to get workspaces created.

## Testing the Fix

After applying:
1. Run any workflow
2. Check that a new worktree appears in `/worktrees/`
3. Verify logs show "Created workspace for run..."
4. Confirm workspace_path is not None in execution