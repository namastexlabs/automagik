# Claude Code In-Place Workspace Flag Implementation Plan

**Epic**: Add in-place workspace flag for Claude Code workflows  
**Branch**: `feature/claude-code-inplace-workspace`  
**Priority**: High  
**Type**: Simple Feature (KISS approach with .env flag)

## Problem Analysis

Current Claude Code workflows copy the entire workspace to isolated directories for execution. However, workflows like BRAIN and LINA only read/write documentation and manage external APIs - they don't need this expensive isolation.

### Workflow Analysis Results

| Workflow | Needs Isolation? | Reason |
|----------|------------------|---------|
| **BRAIN** | ❌ No | Only reads reports, writes minimal docs, uses MCP memory tools |
| **LINA** | ❌ No | Only manages Linear tasks via API, reads completion reports |
| **BUILDER** | ✅ Yes | Creates production systems, runs builds, 7 parallel subagents |
| **GUARDIAN** | ✅ Yes | Runs tests, security scans, performance checks |
| **SURGEON** | ✅ Yes | Makes code changes, runs fixes and optimizations |
| **SHIPPER** | ✅ Yes | Handles deployments, creates production configs |

## KISS Technical Implementation (Simple .env Flag)

### Single Change Point
**File**: `src/agents/claude_code/repository_utils.py`
- Add environment variable check in `setup_repository()` function
- Skip git clone/copy when `current_workspace=true` in .env
- Use current working directory as workspace

### Implementation Details
```python
# In setup_repository() function at line 42
if os.getenv("CLAUDE_CURRENT_WORKSPACE", "false").lower() == "true":
    return await _use_current_workspace(workspace, branch)

# New helper function
async def _use_current_workspace(workspace: Path, branch: str) -> Path:
    """Use current working directory as workspace."""
    current_repo = await find_repo_root()
    if not current_repo:
        raise RuntimeError("Not in a git repository")
    logger.info(f"Using current workspace: {current_repo}")
    return current_repo
```

### Usage
```bash
# Enable in-place workspace
export CLAUDE_CURRENT_WORKSPACE=true
# Or add to .env file: current_workspace=true

# Run any workflow - will use current directory
# No other changes needed
```

## What This Approach Eliminates
- ❌ No API parameter passing through multiple layers
- ❌ No model schema changes and validation  
- ❌ No workflow prompt modifications
- ❌ No multiple component updates
- ❌ No complex parallel workflow orchestration

## Benefits of Simple Approach
- ✅ Single environment variable check (3 lines)
- ✅ One helper function (8 lines)
- ✅ Zero API changes
- ✅ 15 minutes implementation
- ✅ Easy rollback (toggle env var)
- ✅ Works with all workflows instantly

## Simple Implementation Strategy

### Single Task: BUILDER workflow (15 minutes)
1. Modify `repository_utils.py` with environment variable check
2. Add helper function for current workspace usage
3. Test with LINA/BRAIN workflows using `.env` file

### Implementation Steps
```bash
# 1. Add environment check to repository_utils.py (3 lines)
# 2. Add helper function (8 lines) 
# 3. Test with: echo "current_workspace=true" >> .env
# 4. Run LINA workflow to verify in-place execution
```

### No Complex Orchestration Needed
This is a simple 11-line code change, not a multi-hour epic requiring:
- ❌ Parallel workflow coordination
- ❌ API design and model changes
- ❌ Multiple component updates
- ❌ Complex testing scenarios

## Success Criteria (Simple)

### Functional Requirements
- ✅ LINA/BRAIN workflows run in-place when `current_workspace=true` in .env
- ✅ Other workflows continue using isolated workspaces (default behavior)
- ✅ No regression in existing workspace copying behavior

### Performance Requirements  
- ✅ In-place workflows start 5-10x faster (no rsync copying)
- ✅ Reduced disk space usage for LINA/BRAIN executions

### Safety Requirements
- ✅ Environment variable defaults to false (safe by default)
- ✅ Easy rollback by removing/changing .env variable

## Implementation Timeline

| Task | Duration | Files Changed | Deliverable |
|------|----------|---------------|-------------|
| Code Change | 15 minutes | 1 file | 11 lines of code |
| Testing | 5 minutes | N/A | Verify LINA works in-place |
| **Total** | **20 minutes** | **1 file** | **Production ready** |

## Git Strategy

- **Branch**: Current branch (no need for feature branch)
- **Commit**: Single commit with the 11-line change
- **Test**: Run LINA with `.env` flag to verify

This is a simple environment variable check, not a complex system enhancement requiring orchestration.