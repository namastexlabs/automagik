# CRITICAL: Workflow Directory Bug Fix

## Bug Description
**Issue**: Claude Code workflows are copying the entire project **INTO** the workflows folder instead of copying to the configured workspace location.

**Expected**: Copy to `CLAUDE_LOCAL_WORKSPACE=/home/namastex/claude-workspace`  
**Actual**: Copying to `src/agents/claude_code/workflows/*/workflow/am-agents-labs/`

**Impact**: 
- 6GB of wasted disk space (3.9GB + 2.0GB duplicates)
- Recursive directory nesting causing infinite loops
- Test timeouts from accessing massive nested structures
- Broken workflow isolation

## Root Cause Analysis

The workflow system should:
1. Read `CLAUDE_LOCAL_WORKSPACE` from environment
2. Copy/link project to that external directory  
3. Execute Claude Code in the external workspace
4. **NOT** create nested copies inside the source tree

## Immediate Actions

### 1. Emergency Cleanup (Save 6GB)
```bash
# Remove the incorrectly placed copies
rm -rf src/agents/claude_code/workflows/test/workflow/am-agents-labs/
rm -rf src/agents/claude_code/workflows/architect/workflow/am-agents-labs/

# Verify workspace directory exists and is being used
ls -la /home/namastex/claude-workspace/
```

### 2. Find the Bug Location
**Files to check**:
- `src/agents/claude_code/agent.py` - main workflow orchestration
- `src/agents/claude_code/cli_executor.py` - CLI execution logic  
- `src/agents/claude_code/workflows/*/` - individual workflow configs
- Any container or workspace setup code

### 3. Check Workspace Configuration Loading
```bash
# Verify environment loading in workflow code
uv run python -c "import os; print('CLAUDE_LOCAL_WORKSPACE:', os.getenv('CLAUDE_LOCAL_WORKSPACE'))"
```

## Files That Need Investigation

### Workspace Setup Logic
- `src/agents/claude_code/agent.py` - how workspace_base is determined
- `src/agents/claude_code/cli_executor.py` - workspace preparation
- Any file containing "workspace" or "workflow/am-agents-labs"

### Environment Loading
- How `.env` is loaded in workflow context
- Whether workflows inherit parent environment correctly
- Container vs local mode workspace handling

### Copy/Link Operations  
- Find code that copies project files to workspace
- Check if it's using relative vs absolute paths incorrectly
- Verify it respects `CLAUDE_LOCAL_WORKSPACE` setting

## Expected Fix

The workflow system should:

```python
# CORRECT behavior
workspace_base = os.getenv('CLAUDE_LOCAL_WORKSPACE', '/tmp/claude-workspace')
# Copy project to: /home/namastex/claude-workspace/
# NOT to: src/agents/claude_code/workflows/*/workflow/am-agents-labs/
```

## Verification Steps

After fixing:
1. **Environment check**: `echo $CLAUDE_LOCAL_WORKSPACE`
2. **No nested copies**: `find src/ -name "am-agents-labs" -type d | wc -l` should be 0
3. **Correct workspace**: `ls /home/namastex/claude-workspace/` should show project copy
4. **Test pass**: Workspace path test should pass with correct path
5. **Disk space**: `du -sh src/` should be much smaller

## Related Issues This Fixes

1. **Test failure**: `test_agent.py:53` workspace path mismatch
2. **Test timeouts**: No more recursive directory traversal
3. **Disk space**: Recover 6GB immediately  
4. **Workflow isolation**: Proper external workspace usage
5. **Performance**: Faster test execution without massive directories

This is the root cause of many testing issues and needs immediate attention.