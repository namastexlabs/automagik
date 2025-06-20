# 🔴 ROOT CAUSE ANALYSIS - Workflow Workspace Bug

## The Complete Picture

### 1. **Missing Workspace Creation Step**

The workflow execution flow is missing the crucial workspace creation step:

```
API Request → Create Run → Execute Workflow → ❌ MISSING: Create Workspace → Run Claude SDK
```

### 2. **ID Mapping Disconnect**

```python
# What happens:
1. Workspace created with: active_workspaces[run_id] = path
2. Claude returns: claude_session_id 
3. Lookup attempts: active_workspaces[claude_session_id] → None
```

### 3. **Persistent Workspace Reuse Problem**

When `persistent=True`:
- First run creates workspace and tracks it with run_id_1
- Second run reuses workspace but doesn't add run_id_2 to tracking
- Only the original run_id_1 can find the workspace

### 4. **The Actual Bug Location**

Looking at the code flow:
1. **agent.py:execute_workflow()** - Creates request but doesn't create workspace
2. **sdk_executor.py:execute_claude_task()** - Uses workspace from agent_context
3. **agent_context['workspace']** - Set to kwargs.get('workspace_path', '.') 
4. **No call to CLIEnvironmentManager.create_workspace()**

## The Fix Needed

The workspace needs to be created BEFORE calling the SDK executor:

```python
# In agent.py, before executing:
if self.executor.environment_manager:
    workspace_path = await self.executor.environment_manager.create_workspace(
        run_id=run_id,
        workflow_name=workflow_name,
        persistent=kwargs.get('persistent', True),
        git_branch=kwargs.get('git_branch')
    )
    
    # Update agent_context with actual workspace
    agent_context['workspace'] = str(workspace_path)
    
    # ALSO: Map the run_id to track this workspace
    # So it can be found later regardless of Claude session ID
```

## Why Only 2 Persistent Folders Exist

The worktrees directory only has `builder_persistent` and `surgeon_persistent` because:
1. These were created in previous successful runs
2. New runs are failing to create workspaces
3. The code reuses existing persistent workspaces when found
4. But new session-specific workspaces are never created

## Impact

- ALL workflows are affected
- No new worktrees are being created
- Git operations fail (no workspace)
- Auto-commit can't find workspace
- Workflows appear to complete but without proper execution environment