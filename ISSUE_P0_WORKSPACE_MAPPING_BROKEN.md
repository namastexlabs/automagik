# 🚨 P0 CRITICAL: Workspace Mapping System Completely Broken

## Issue Summary
**The workspace mapping system cannot connect run_ids to workspace paths, causing all git operations and workspace isolation to fail.**

## Evidence from Logs
```bash
# SYSTEM INITIALIZATION: ✅ WORKING
CLIEnvironmentManager initialized with base path: /home/namastex/workspace/am-agents-labs/worktrees

# WORKSPACE DETECTION: ❌ BROKEN  
AUTO-COMMIT: Active workspaces: []
AUTO-COMMIT: Workspace path for run_id=2dd481d7-818e-42a9-b296-e112daca8dcd, claude_session_id=f2ad20af-e260-4400-aa15-55afa57833f5: None
WARNING: No workspace path found for run 2dd481d7-818e-42a9-b296-e112daca8dcd
```

## Discovery Analysis
**The worktree directories ARE being created, but in the wrong location:**

### Expected Location:
```bash
/home/namastex/workspace/am-agents-labs/worktrees/guardian_persistent/
```

### Actual Location:
```bash
# Claude session files are in:
/home/namastex/.claude/projects/-home-namastex-workspace-am-agents-labs-worktrees-guardian-persistent/

# Claude cache files are in:
/home/namastex/.cache/claude-cli-nodejs/-home-namastex-workspace-am-agents-labs-worktrees-guardian-persistent/
```

## Root Cause Analysis
```python
# The issue sequence:
1. ✅ CLIEnvironmentManager initializes with correct base path
2. ✅ Workflow executes successfully using Claude SDK  
3. ❌ Workspace path mapping fails - returns None
4. ❌ Auto-commit cannot find workspace to commit changes
5. ❌ Git operations fail despite successful workflow execution

# The mapping system is looking for:
workspace_path = get_workspace_path(run_id, claude_session_id)
# But returns: None

# Meanwhile, Claude SDK creates workspaces in its own directories:
# ~/.claude/projects/ and ~/.cache/claude-cli-nodejs/
```

## Critical Impact
- **ALL git operations fail**: No commits, no workspace isolation
- **Workspace isolation broken**: Files not created in expected locations  
- **Auto-commit completely non-functional**: Cannot find workspace to commit
- **File persistence issues**: Work may be lost between sessions

## Affected Functionality
1. **Git integration**: ❌ Completely broken
2. **Workspace isolation**: ❌ Wrong directories
3. **File persistence**: ❌ Files in Claude cache, not project
4. **Auto-commit**: ❌ Cannot find workspace
5. **Cross-session continuity**: ❌ Workspace mapping lost

## Technical Investigation Required
```python
# Files to investigate:
1. src/agents/claude_code/cli_environment.py - CLIEnvironmentManager  
2. src/agents/claude_code/agent.py - Workspace path mapping logic
3. src/agents/claude_code/sdk_executor.py - Claude SDK workspace creation

# Key questions:
1. Why is Claude SDK creating workspaces in ~/.claude/ instead of project worktrees/?
2. How is workspace_path supposed to be mapped from run_id + claude_session_id?
3. Is there a disconnect between SDK workspace creation and our tracking?
```

## Business Impact
- **CRITICAL**: Git integration completely non-functional
- **HIGH**: Workspace isolation not working as designed
- **HIGH**: File persistence unreliable
- **MEDIUM**: Auto-commit features disabled

## Immediate Investigation Steps
1. **Trace workspace creation**: Follow Claude SDK workspace creation process
2. **Check mapping logic**: Verify run_id → workspace_path mapping
3. **Review CLI environment**: Ensure proper workspace coordination
4. **Test workspace persistence**: Verify files are created where expected

## Proposed Fix Strategy
```python
# Option 1: Fix mapping to find Claude SDK workspaces
def get_workspace_path(run_id, claude_session_id):
    # Map to actual Claude workspace locations
    return f"~/.claude/projects/-home-namastex-workspace-am-agents-labs-worktrees-{workflow}-persistent/"

# Option 2: Force Claude SDK to use our workspace directories
claude_config = {
    'workspace_base': '/home/namastex/workspace/am-agents-labs/worktrees'
}

# Option 3: Hybrid approach - sync between Claude workspaces and our directories
def sync_workspace_files(claude_workspace, project_workspace):
    # Copy files between locations as needed
```

## Acceptance Criteria
- [ ] Workspace path mapping returns valid paths, not None
- [ ] Active workspaces list shows actual workspaces  
- [ ] Files created in expected project worktree directories
- [ ] Auto-commit can find and commit workspace changes
- [ ] Git operations work within workspace isolation

## Risk Level: CRITICAL 🚨
**Workspace isolation and git integration are core features that are completely broken.**

## Files Created But Mislocated
```bash
# These directories exist but in wrong locations:
~/.claude/projects/-home-namastex-workspace-am-agents-labs-worktrees-guardian-persistent/
~/.claude/projects/-home-namastex-workspace-am-agents-labs-worktrees-surgeon-persistent/
# ... all 7 workflows have directories in ~/.claude/projects/
```

**The workspaces ARE being created, just not where the system expects to find them!**