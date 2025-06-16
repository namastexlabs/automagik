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

---

## CRITICAL: New Stuck Workflow Evidence (2025-06-16)

### BUILDER Workflow Initialization Bug - CONFIRMED PATTERN

**Current Incident**: run_5fbae44ab6f0
- **Started**: 2025-06-16 13:31:01 UTC  
- **Current Runtime**: 40+ minutes and counting
- **Status**: Stuck in initialization phase
- **Progress**: 0 turns, 0% completion
- **Cache Efficiency**: 93.6% (indicates active processing)
- **Final Output**: "Now let me run the installation script to set everything up:"

### Critical Pattern Analysis

**Identical Stuck Pattern**:
```
run_5fbae44ab6f0 (BUILDER) - 40+ min, 0 turns, initialization
run_02c9ab1d9675 (BUILDER) - 2+ days, 0 turns, initialization  
run_44007c29a97f (BUILDER) - 2+ days, 0 turns, initialization
run_0dcbc991c0d4 (LINA)    - 2+ days, 0 turns, initialization
```

**Key Evidence**:
1. **High Cache Efficiency**: 93.6% shows workflows ARE processing
2. **Zero Turn Count**: Never complete initialization to first turn
3. **Same Final Output**: All stop at "installation script" or similar
4. **Multiple Workflow Types**: Affects BUILDER, LINA, BRAIN, TEST, ARCHITECT

### Initialization Bug Hypothesis

**Root Cause**: Workflows get stuck in pre-turn initialization loop
- High cache reads suggest repetitive processing
- Never advance to turn 1 conversation
- Likely infinite loop in workflow setup/validation
- All workflows affected, not persona-specific

### IMMEDIATE ACTION REQUIRED

**Classification System**:
- **Stuck**: >30 minutes, 0 turns, initialization phase
- **Slow**: >10 minutes but progressing through turns  
- **Normal**: <10 minutes to first turn

**Urgent Needs**:
1. **Kill Function**: Terminate run_5fbae44ab6f0 immediately
2. **Timeout Detection**: Auto-kill workflows stuck >30 min in initialization
3. **Alternative Approach**: Manual Linear epic creation while BUILDER stuck
4. **Prevention**: Fix initialization loop in all workflow types

### Case Study Documentation

This is definitive proof that workflow initialization has a critical bug affecting all workflow types. The pattern is consistent and reproducible.

---

## New Issues Discovered (2025-06-14)

### Workflow Persona Persistence Problem

**Issue**: LINA lost her persona identity during multi-turn conversation, reverted to base Claude Code identity.

**Investigation Needed**:
- Research `claude -p` command for prompt appending/persona reinforcement
- Check if workflow prompts need explicit persona reinforcement between turns
- Test if session continuity preserves character context properly

**Technical Task**:
```bash
# Need to find the correct claude command flag for prompt persistence
claude -p [persona_file] --append-context
# OR
claude --persona [file] --maintain-context
# OR  
claude --system-prompt [file] --session-persist
```

### Multi-Turn Memory Testing

**Test Plan**:
1. Start conversation with LINA (turn 1)
2. Wait 5+ minutes 
3. Continue conversation (turn 2)
4. Test if she remembers turn 1 context
5. Verify persona persistence across time gaps
6. Document memory retention patterns

**Expected Issues**:
- Context window limitations
- Session timeout problems
- Persona drift over multiple turns
- Memory fragmentation

### Priority Order Tomorrow:
1. **CRITICAL**: Create Linear epic for workflow management (manual creation)
2. **CRITICAL**: Implement workflow kill functionality - 7+ stuck workflows need termination
3. **HIGH**: Fix workflow initialization loop bug (affects all workflow types)
4. **HIGH**: Add timeout detection (auto-kill stuck workflows >30min)
5. **MEDIUM**: Investigate claude -p command options
6. **MEDIUM**: Multi-turn memory persistence testing

---

## Documentation Created (2025-06-16)

**Analysis Report**: `/home/namastex/workspace/am-agents-labs/docs/development/workflow-management/WORKFLOW_INITIALIZATION_BUG_ANALYSIS.md`

This comprehensive report provides:
- Complete case study of run_5fbae44ab6f0 (40+ min stuck BUILDER)
- Pattern analysis across 7+ stuck workflows  
- Root cause hypothesis (initialization loop)
- Classification system for stuck vs slow workflows
- Technical requirements for kill functionality
- Business impact assessment
- Immediate and long-term recommendations

**Use this report as foundation for Linear epic creation and technical implementation planning.**