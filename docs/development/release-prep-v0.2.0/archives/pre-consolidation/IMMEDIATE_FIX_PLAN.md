# IMMEDIATE FIX: Remove Workflow Artifacts

## Root Cause Identified ✅

**The workflow system is working correctly!** It properly copies to:
- `CLAUDE_LOCAL_WORKSPACE=/home/namastex/claude-workspace/claude-code-run_*/am-agents-labs/`

**The real problem**: Leftover artifacts in source tree that get copied with each run:
- `src/agents/claude_code/workflows/test/workflow/am-agents-labs/` (3.9GB)
- `src/agents/claude_code/workflows/architect/workflow/am-agents-labs/` (2.0GB)

These create massive workspace copies (up to 6.8GB per run) because the rsync includes these artifacts.

## Immediate Actions

### 1. Emergency Cleanup (Save 6GB + Fix Workspaces)
```bash
# Remove the source tree artifacts (these should NEVER be in source control)
rm -rf src/agents/claude_code/workflows/test/workflow/am-agents-labs/
rm -rf src/agents/claude_code/workflows/architect/workflow/am-agents-labs/

# Verify removal
find src/agents/claude_code/workflows/ -name "am-agents-labs" -type d
# Should return nothing
```

### 2. Clean Existing Bloated Workspaces
```bash
# Remove all existing workspaces (they're bloated with artifacts)
rm -rf /home/namastex/claude-workspace/claude-code-run_*/

# Fresh workspaces will be much smaller without the artifacts
```

### 3. Fix Test Expectations
**File**: `tests/agents/claude_code/test_agent.py:53`
**Change**:
```python
# From:
workspace_base="/tmp/claude-workspace"
# To:
workspace_base=os.getenv('CLAUDE_LOCAL_WORKSPACE', '/tmp/claude-workspace')
```

### 4. Remove Legacy Files
```bash
# Remove actual legacy _old.py files
rm -f src/agents/pydanticai/*/agent_old.py
```

## Verification Steps

### 1. Test Workspace Creation
```bash
# After cleanup, test that workspaces are created correctly and are small
uv run pytest tests/agents/claude_code/test_agent.py::TestClaudeCodeAgentInitialization::test_agent_initialization -v
```

### 2. Check New Workspace Sizes
```bash
# New workspaces should be ~500MB instead of 6GB
ls -la /home/namastex/claude-workspace/
du -sh /home/namastex/claude-workspace/claude-code-run_*/am-agents-labs/ | head -3
```

### 3. Source Tree Size Reduction
```bash
# Source tree should be much smaller
du -sh src/agents/claude_code/workflows/
# Should be ~50MB instead of 6GB
```

## Why This Happened

The artifacts were likely created during development/testing when:
1. A workflow was run from inside the source tree
2. The copy operation incorrectly created nested directories
3. These got committed accidentally
4. Every subsequent run copies these artifacts, making workspaces massive

## Prevention

### .gitignore Update
Add to `.gitignore`:
```
# Prevent workflow artifacts in source tree
src/agents/claude_code/workflows/*/workflow/am-agents-labs/
src/agents/claude_code/workflows/*/workflow/.env
```

### Workspace Directory Structure
Correct structure after fix:
```
src/agents/claude_code/workflows/
├── architect/
│   ├── prompt.md
│   └── workflow/ (empty - used as temp copy destination)
├── test/
│   ├── prompt.md  
│   └── workflow/ (empty - used as temp copy destination)
```

External workspace (correct):
```
/home/namastex/claude-workspace/
└── claude-code-run_*/
    └── am-agents-labs/ (clean copy without artifacts)
```

## Expected Results

After this fix:
- [ ] Source tree reduced by 6GB
- [ ] New workspaces ~500MB instead of 6GB  
- [ ] Test passes with correct workspace path
- [ ] No more recursive directory nesting
- [ ] Faster rsync operations (much less data to copy)

This addresses the core issue and will dramatically improve performance and disk usage.