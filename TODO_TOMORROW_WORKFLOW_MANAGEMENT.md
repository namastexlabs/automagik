# TODO: Workflow Management Features Needed

**Priority**: High  
**Date**: 2025-06-14  

## Missing Critical Feature: Kill Running Workflows

### Problem
- LINA workflow stuck (run_0dcbc991c0d4) - running for 10+ minutes with 0 progress
- No way to terminate/cancel running workflow instances
- Workflows can get stuck in infinite loops or waiting states
- Need manual intervention capability

### Required Implementation
Add to `mcp__automagik-workflows__` MCP server:

```python
# New function needed
def kill_workflow(run_id: str) -> dict:
    """Terminate a running workflow instance"""
    # Force stop the workflow process
    # Clean up resources
    # Return status confirmation

# New function needed  
def restart_workflow(run_id: str) -> dict:
    """Kill and restart a workflow with same parameters"""
    # Kill existing instance
    # Start new instance with same config
    # Return new run_id
```

### API Endpoints Needed
- `mcp__automagik-workflows__kill_workflow(run_id)`
- `mcp__automagik-workflows__restart_workflow(run_id)`
- `mcp__automagik-workflows__force_complete_workflow(run_id)` (mark as failed/completed)

### Use Cases
1. **Stuck Workflows**: Like current LINA situation
2. **Infinite Loops**: When workflows get caught in logic loops
3. **Resource Management**: Free up stuck processes
4. **Development**: Quick restart during prompt/logic debugging

### Current Workaround Needed
- Check if workflow process can be killed via system commands
- Manually mark workflow as failed in database
- Restart with new instance

---

## Additional Workflow Management Features

### Workflow Monitoring Dashboard
- Real-time progress tracking
- Resource usage monitoring  
- Automatic stuck detection
- Health check endpoints

### Workflow Debugging
- Step-by-step execution logging
- Breakpoint insertion capability
- Variable state inspection
- Manual step-through mode

### Workflow Recovery
- Automatic retry on failure
- Checkpoint/resume capability
- State persistence across restarts
- Error recovery strategies

---

**Immediate Need**: Kill stuck LINA workflow and restart the Linear epic simplification task