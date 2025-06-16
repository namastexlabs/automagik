# BUILDER Workflow - Emergency Kill Implementation

## 🚨 NEXT STEP: Run BUILDER Workflow

Based on LINA's successful epic creation, here's the exact dispatch text for BUILDER:

---

## BUILDER Manual Spawn Dispatch

### Context
- **Linear Epic**: [NMSTX-308](https://linear.app/namastex/issue/NMSTX-308/critical-workflow-management-system-issues) ✅ Created
- **Emergency Status**: BUILDER workflow `run_5fbae44ab6f0` stuck 40+ minutes
- **Critical Mission**: Implement emergency kill functionality immediately

### Dispatch Text for Manual BUILDER Spawn:

```
You are BUILDER, tasked with implementing emergency workflow kill functionality to resolve critical system issues.

## URGENT MISSION - LINEAR CONTEXT
Working on Linear epic NMSTX-308: "🚨 CRITICAL: Workflow Management System Issues"
Epic URL: https://linear.app/namastex/issue/NMSTX-308/critical-workflow-management-system-issues

## CRITICAL EMERGENCY SITUATION
**Stuck Workflow**: run_5fbae44ab6f0 (BUILDER) - 40+ minutes stuck in initialization
**System Impact**: Workflow orchestration partially impaired, blocking all development
**Root Cause**: Initialization loop bug affecting multiple workflow types

## PRIMARY OBJECTIVE: EMERGENCY KILL IMPLEMENTATION

### 1. Immediate Kill Function (URGENT)
Implement `mcp__automagik_workflows__kill_workflow(run_id)` function to:
- Terminate stuck workflow run_5fbae44ab6f0 immediately
- Add three kill phases: Graceful (SIGTERM) → Forced (SIGKILL) → System cleanup
- Return kill confirmation and cleanup status

### 2. Process Tracking System (CRITICAL)
Add workflow process tracking to database:
```sql
CREATE TABLE workflow_processes (
    run_id TEXT PRIMARY KEY,
    pid INTEGER,
    status TEXT,
    started_at TIMESTAMP,
    workspace_path TEXT,
    last_heartbeat TIMESTAMP
);
```

### 3. Integration with Existing System (HIGH)
- Modify MCP automagik-workflows server to expose kill_workflow endpoint
- Integrate with LocalExecutor/ClaudeExecutor for process management
- Add process registration during workflow startup
- Implement proper cleanup and resource management

## TECHNICAL IMPLEMENTATION REQUIREMENTS

Based on analysis in `/home/namastex/workspace/am-agents-labs/docs/development/workflow-kill-system/`:

### Emergency Kill Function:
```python
async def kill_workflow(run_id: str, force: bool = False) -> dict:
    """
    Emergency workflow termination with progressive kill phases:
    1. Graceful shutdown (5s timeout)
    2. Forced termination (10s timeout)  
    3. System cleanup (resource cleanup)
    
    Returns:
        {
            "success": bool,
            "run_id": str,
            "killed_at": timestamp,
            "cleanup_status": dict,
            "message": str
        }
    """
```

### Process Tracking:
```python
class WorkflowProcessTracker:
    def register_process(self, run_id: str, pid: int, workspace: str):
        """Register workflow process for kill capability"""
        
    async def emergency_kill(self, run_id: str) -> dict:
        """Emergency termination for stuck workflows"""
```

## IMMEDIATE ACTIONS REQUIRED

### Step 1: Implement Emergency Kill (Priority 1)
- Create kill_workflow MCP function
- Add to automagik-workflows server
- Test with stuck run_5fbae44ab6f0

### Step 2: Add Process Tracking (Priority 2)  
- Create database schema
- Integrate with workflow executors
- Track active processes

### Step 3: Validate System Recovery (Priority 3)
- Confirm stuck workflow terminated
- Verify no orphaned processes
- Test new workflow creation

## SUCCESS CRITERIA
- run_5fbae44ab6f0 successfully killed and cleaned up
- Kill functionality available via MCP for future use
- Process tracking operational for new workflows
- System resource consumption normalized
- No regression in existing workflow functionality

## CONTEXT REFERENCES
- Epic documentation: /docs/development/workflow-kill-system/
- Technical analysis: /docs/development/workflow-kill-system/context.md
- Implementation details: /docs/development/workflow-kill-system/manual-spawn-tasks.md

## HANDOFF TO GUARDIAN
After successful implementation:
- Document kill functionality usage
- Provide test cases for GUARDIAN validation
- Report implementation status to Linear epic NMSTX-308

## FELIPE'S SECURITY REQUIREMENTS
- Explicit error handling for all kill operations
- Comprehensive validation before termination
- Audit trail for all kill attempts
- Safe resource cleanup validation

## CEZAR'S ARCHITECTURE REQUIREMENTS  
- Clean separation between kill logic and workflow execution
- Scalable process tracking system
- Robust error recovery mechanisms
- Framework-consistent integration patterns

CRITICAL STATUS: Immediate implementation required to restore workflow orchestration functionality.
```

---

## Why BUILDER Next?

1. **Emergency Priority**: `run_5fbae44ab6f0` consuming resources for 40+ minutes
2. **Blocking Issue**: BUILDER workflows non-functional, blocking all implementation work  
3. **Foundation Requirement**: Kill functionality needed before GUARDIAN can validate safety
4. **Linear Coordination**: LINA successfully created epic structure for tracking

## Expected Outcome

After BUILDER completes:
- Stuck workflow `run_5fbae44ab6f0` terminated
- Emergency kill functionality available
- System resources freed up
- Ready for GUARDIAN safety validation and timeout detection

## Timing Estimate
45-60 minutes for complete emergency kill implementation and stuck workflow termination.