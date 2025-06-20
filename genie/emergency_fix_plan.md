# 🚨 EMERGENCY FIX PLAN - Workflow System Recovery

## Critical Issue Summary

The workflow system has a **circular dependency bug**:
- Workflows can't run because workspaces aren't created
- We can't fix the bug using a workflow because... workflows can't run!

## Manual Fix Required

Since SURGEON workflow can't execute due to the same bug it needs to fix, we need manual intervention.

### The Fix Location

**File**: `src/agents/claude_code/agent.py`
**Method**: `execute_workflow` (around line 700-850)
**Problem**: No workspace is created before SDK execution

### What's Missing

```python
# Current flow (BROKEN):
agent_context = {
    'workspace': kwargs.get('workspace_path', '.'),  # Always '.'
    ...
}
# Goes directly to SDK executor with no actual workspace

# Should be:
# 1. Create workspace using CLIEnvironmentManager
workspace_path = await self.executor.environment_manager.create_workspace(
    run_id=run_id,
    workflow_name=workflow_name,
    persistent=kwargs.get('persistent', True)
)

# 2. Update agent_context with real workspace
agent_context = {
    'workspace': str(workspace_path),
    ...
}
```

## Recovery Steps

1. **Manual Code Fix**: Edit agent.py directly to add workspace creation
2. **Test Fix**: Run a simple workflow to verify workspaces are created
3. **Run SURGEON**: Once working, use SURGEON to properly implement the fix
4. **Verify System**: Check all workflows can execute properly

## Why This Happened

1. The workspace creation logic exists in CLIEnvironmentManager
2. But it's never called during workflow execution
3. The SDK executor expects a workspace but gets '.' (current directory)
4. This affects ALL workflows universally

## Lessons Learned

- Critical infrastructure bugs can create circular dependencies
- Need emergency manual intervention procedures
- Workflow system should have self-healing capabilities
- Consider a "bootstrap" mode for fixing core issues