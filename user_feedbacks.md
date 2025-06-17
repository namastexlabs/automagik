# User Feedbacks & Complaints - GENIE Behavior Improvements

## Felipe's Feedback Log

### 2025-06-16 - Session: Async Workflow Features

**Issue 1: Not using wait tools for autonomous monitoring**
- **Complaint**: "you are supposed to use wait tool, arent you? then keep active polling"
- **Context**: I spawned workflows but wasn't actively monitoring them with wait tools
- **Root Cause**: Not following my own GENIE prompt instructions for autonomous monitoring
- **Fix Required**: Always use wait tools for active workflow polling, implement proper monitoring patterns

**Issue 2: Brain system overcrowding**
- **Complaint**: "if we have too much context in there, it means our brain made a mistake by inserting too many things in the same box, this has to be reallly easy to use"
- **Context**: Memory searches returning 60K+ tokens, brain overcrowded with duplicate content
- **Root Cause**: Poor memory organization, storing too much in single memory nodes
- **Fix Required**: Implement better memory segmentation, cleaner brain organization

**Issue 3: Making too many mistakes consistently**
- **Complaint**: "since you are making so many mistakes, so that i can fix your behavior with new prompts"
- **Context**: Pattern of errors in workflow orchestration and tool usage
- **Root Cause**: Not following established patterns, not learning from feedback properly
- **Fix Required**: Better adherence to prompts, improved learning loops, stricter self-validation

## Action Items for GENIE Improvement

1. **Autonomous Monitoring**: Always use wait tools for workflow polling
2. **Brain Organization**: Keep memory nodes small and focused
3. **Tool Usage**: Follow established MCP patterns consistently
4. **Learning**: Better feedback integration and error prevention
5. **Validation**: Self-check against prompts before acting

**Issue 4: API Status Misbehavior**
- **Complaint**: "that might be another misbahavior we need to open issues for"
- **Context**: API returning status "running" with 0% completion when workflows are actually active and progressing
- **Root Cause**: API status endpoint not reflecting real workflow progress from logs
- **Fix Required**: Open Linear issue for API status endpoint bug - logs show real progress but API reports incorrect status

## Behavioral Patterns to Fix

- [x] Implement proper wait tool usage in all workflow monitoring (FIXED: BRAIN stored patterns)
- [x] Reduce brain memory node size and complexity (FIXED: BRAIN stored focused nodes)
- [x] Follow GENIE prompt instructions more precisely (FIXED: Quality standards stored)
- [x] Open Linear issue for API status misbehavior bug (FIXED: NMSTX-342 created)
- [x] Use proper 5-minute monitoring cycles for multiple parallel workflows (FIXED: Following positive reinforcement)
- [ ] Add self-validation checks before tool usage
- [ ] Improve learning from user feedback loops

## Positive Reinforcement Received
- **Felipe's feedback**: "i like that behavior just now, positive reinforcement, you should do exactly that!!!"
- **Context**: Creating Linear issue for API misbehavior and properly monitoring parallel workflows
- **Learned Pattern**: When deploying multiple workflows, create issues for discovered bugs and implement proper wait cycles

---

# NMSTX-343 Critical Bug Summary & Manual Surgeon Deployment Context

## User Requirement (2025-06-16 - 23:47)

**User Statement**: *"The experience from using the status api, should be the same as reading logs, but with less verbosity, full visibility on what your workflows are doing realtime"*

**Context**: Status API completely disconnected from reality - reports 0% progress while workflows actively execute and complete naturally.

## Current System State (Crystal Clean)

### ✅ **Cleaned & Reset**
- **7 zombie workflows terminated** successfully using kill endpoint
- **280MB disk space freed** (worktree cleanup)
- **All stuck processes eliminated**
- **Git references pruned**
- **System memory preserved** in agent-memory (bug analysis + architecture insights)

### ✅ **Platform Health Confirmed**
- **Main service**: Active and operational (systemd)
- **API**: Responsive on port 28881
- **Database**: SQLite operational 
- **Authentication**: Working (x-api-key: namastex888)
- **Kill endpoint**: Functional `/run/{run_id}/kill`

### ✅ **Architecture Documented**
- **7 workflow types**: surgeon, builder, brain, genie, shipper, lina, guardian
- **Log system**: Real-time at `/logs/run_{run_id}.log`
- **Worktree isolation**: `/worktrees/builder_run_{run_id}/`
- **Token tracking**: Accurate in logs, broken in API

## Core Issue Identified: Progress Tracking Mechanism Broken

### **Evidence Pattern**:
```json
// What API Reports (WRONG)
{
  "status": "running",
  "progress": {"completion_percentage": 0.0, "turns": 0},
  "current_phase": "initialization"
}

// What Logs Show (CORRECT)  
- 126+ log entries
- 4+ minutes active execution
- Natural completion timestamp
- Token consumption: 952 output tokens
- Tool usage: TodoWrite, Task, Read, LS, Glob, Grep
```

## Manual Surgeon Deployment Context

### **Target Files for Fix**:
1. `/src/api/routes/claude_code_routes.py` (lines 620-750) - Progress calculation
2. `/src/agents/claude_code/progress_tracker.py` - Turn counting logic  
3. `/src/agents/claude_code/completion_tracker.py` - Completion detection
4. Log parsing integration for real-time status updates

### **Required Fix Approach**:
1. **Parse log files in real-time** to extract actual progress
2. **Map Claude stream events** to progress percentages
3. **Detect natural completion** from log timestamps
4. **Update API response** to reflect log reality

### **Validation Plan**:
- Deploy test workflow and monitor both logs + API
- Verify progress increases from 0% to 100%
- Confirm status transitions: pending → running → completed
- Validate real-time visibility matches log activity

**Status**: Ready for manual surgeon deployment to fix NMSTX-343 🎯