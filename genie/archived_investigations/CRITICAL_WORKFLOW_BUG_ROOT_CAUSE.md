# 🚨 CRITICAL WORKFLOW BUG - ROOT CAUSE IDENTIFIED

## Summary
The workspace_path is NULL in the database because **the `WorkflowRunUpdate` model is missing the `workspace_path` field**, preventing the update operation from working.

## Root Cause Analysis

### 1. **The Bug Chain**
1. Workflow creates workspace successfully: `/home/namastex/workspace/am-agents-labs/worktrees/builder_persistent`
2. Code attempts to update database with workspace path (agent.py:853)
3. Update silently fails because `workspace_path` is not in `WorkflowRunUpdate` model
4. Database remains with NULL workspace_path
5. All downstream operations fail (status reporting, cleanup, etc.)

### 2. **Evidence**
- **Test Run**: `45e0be5e-1ba6-406b-8e4c-2021ae676106`
- **Logs show**: "Updated workflow run 45e0be5e-1ba6-406b-8e4c-2021ae676106 with workspace path"
- **Database shows**: `workspace_path = NULL`
- **File created successfully**: `/worktrees/builder_persistent/bug_test.txt`

### 3. **Code Analysis**

#### Missing Field in WorkflowRunUpdate Model
```python
# src/db/models.py (line ~800-836)
class WorkflowRunUpdate(BaseModel):
    # ... other fields ...
    workspace_cleaned_up: Optional[bool] = None
    # MISSING: workspace_path: Optional[str] = None
```

#### Update Function Can't Handle workspace_path
```python
# src/db/repository/workflow_run.py (line ~218-220)
if update_data.workspace_cleaned_up is not None:
    update_fields.append("workspace_cleaned_up = ?")
    params.append(update_data.workspace_cleaned_up)
# No handler for workspace_path because it's not in the model!
```

## The Fix

### 1. **Add to WorkflowRunUpdate Model** (src/db/models.py:~821)
```python
workspace_cleaned_up: Optional[bool] = Field(None, description="Updated cleanup status")
workspace_path: Optional[str] = Field(None, description="Updated workspace path")  # ADD THIS
```

### 2. **Update Repository Handler** (src/db/repository/workflow_run.py:~220)
```python
if update_data.workspace_path is not None:
    update_fields.append("workspace_path = ?")
    params.append(update_data.workspace_path)
```

## Impact
- **All workflows** have NULL workspace_path
- **Status reporting** shows "No workspace path found"
- **Auto-commit** might fail due to workspace lookup issues
- **Cleanup services** can't find workspaces
- **Git operations** may fail

## Testing Proof
1. Created test workflow that successfully created `/worktrees/builder_persistent/bug_test.txt`
2. Logs claimed workspace path was updated
3. Database query confirmed it's still NULL
4. Code inspection revealed the missing field

## Missing Testing Features Needed

### 1. **Direct Database Query MCP Tool**
```python
mcp__sqlite__query_workflow_runs(
    filters={"run_id": "xxx"},
    fields=["workspace_path", "status"]
)
```

### 2. **Workspace Verification Tool**
```python
mcp__workspace__verify(
    run_id="xxx",
    check_db=True,
    check_filesystem=True
)
```

### 3. **Real-time Log Streaming Tool**
```python
mcp__logs__stream(
    run_id="xxx",
    follow=True,
    filter="ERROR|workspace"
)
```

### 4. **Workflow Health Check Tool**
```python
mcp__workflow__health_check(
    run_id="xxx",
    verbose=True
)
```

## Recommendation
This is a simple but critical bug. The fix is straightforward - add the missing field to the model. Without this fix, the entire workflow system is compromised as workspaces can't be tracked properly.