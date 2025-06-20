# ⚠️ P1 HIGH: Workflow Recovery System False Alerts

## Issue Summary
**The workflow recovery system generates false "stuck workflow" alerts for workflows that may be legitimately running or completed.**

## Evidence
```bash
# Recent recovery check showing false alerts:
WARNING: Workflow 5f23ccf9-4893-4703-8e71-e859b4ee78db stuck - no updates for 30+ minutes
WARNING: Workflow ca8ac7d5-f5bc-45ca-8cf3-ba360fc338a2 stuck - no updates for 30+ minutes
INFO: Found 2 potentially stuck workflows
WARNING: Workflow 5f23ccf9-4893-4703-8e71-e859b4ee78db needs manual investigation
WARNING: Workflow ca8ac7d5-f5bc-45ca-8cf3-ba360fc338a2 needs manual investigation
```

## Root Cause Analysis
```python
# File: src/agents/claude_code/workflow_recovery.py
# Issue: Recovery system may not account for:
1. Workflows in legitimate long-running operations
2. Completed workflows with stale database status
3. Workflows paused by user interaction
4. Status reporting bugs affecting "last update" timestamps
```

## Affected Systems
- **Operations team**: False alerts requiring manual investigation
- **Monitoring dashboards**: Shows "stuck" workflows that aren't stuck
- **Resource cleanup**: May terminate legitimate workflows
- **Alert fatigue**: Reduces trust in real stuck workflow alerts

## Technical Investigation Needed
```bash
# Check these workflows specifically:
run_id: 5f23ccf9-4893-4703-8e71-e859b4ee78db
run_id: ca8ac7d5-f5bc-45ca-8cf3-ba360fc338a2

# Questions to answer:
1. What is the actual status of these workflows?
2. Are they truly stuck or legitimately running?
3. Is the "no updates for 30+ minutes" accurate?
4. Are they related to the status reporting bug (P0 issue)?
```

## Business Impact
- **MEDIUM**: Operational overhead from false alerts
- **MEDIUM**: Potential premature termination of legitimate workflows
- **LOW**: Alert fatigue reducing effectiveness of monitoring

## Investigation Plan
1. **Audit specific workflows**: Check actual status vs reported status
2. **Review recovery logic**: Ensure stuck detection is accurate
3. **Cross-reference with P0 bug**: Status reporting may affect recovery timestamps
4. **Test recovery scenarios**: Verify legitimate stuck workflow detection still works

## Proposed Fixes
```python
# Option 1: Improve stuck detection logic
def is_workflow_truly_stuck(workflow_id):
    # Check multiple indicators:
    # - Database status
    # - Process status  
    # - Recent log activity
    # - Claude session activity
    
# Option 2: Add grace periods for different workflow types
STUCK_THRESHOLDS = {
    'guardian': 45,  # minutes
    'surgeon': 30,   # minutes  
    'builder': 60,   # minutes (may run longer)
    'genie': 90,     # minutes (coordination takes time)
}

# Option 3: Manual confirmation before recovery actions
def recovery_requires_confirmation(workflow_id):
    return True  # Always require manual confirmation
```

## Files to Investigate
- `src/agents/claude_code/workflow_recovery.py` - Recovery logic
- `src/db/repository/workflow_run.py` - Status timestamp tracking
- `src/agents/claude_code/agent.py` - Workflow status updates
- Log analysis for the specific flagged workflow IDs

## Acceptance Criteria
- [ ] No false "stuck workflow" alerts
- [ ] Accurate detection of legitimately stuck workflows
- [ ] Proper handling of long-running workflows
- [ ] Clear distinction between stuck, running, and completed workflows
- [ ] Manual confirmation required before any automated recovery actions

## Immediate Actions
1. **DO NOT terminate** the flagged workflows until investigation
2. **Check actual status** of run_ids 5f23ccf9 and ca8ac7d5
3. **Review recovery logic** for false positive causes
4. **Consider disabling automated recovery** until fixes implemented

## Risk Level: HIGH ⚠️
**Could terminate legitimate workflows and create operational overhead.**