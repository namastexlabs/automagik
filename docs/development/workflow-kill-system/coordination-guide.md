# Workflow Kill System - Manual Spawn Coordination Guide

## 🚨 URGENT IMPLEMENTATION STATUS

**Crisis**: Multiple workflows stuck consuming system resources
- `run_5fbae44ab6f0` (BUILDER) - 40+ minutes stuck
- `run_0dcbc991c0d4` (LINA) - 2+ days stuck  
- No existing kill functionality in platform

**Solution**: Manual workflow spawning to implement kill system while fixing initialization loops

---

## MANUAL SPAWN SEQUENCE

### 1. LINA - Linear Epic Creation (START HERE)
```bash
# Manual spawn command for Felipe/Cezar:
# Workflow: lina
# Session: workflow_kill_epic_creation  
# Branch: feature/workflow-kill-system
# Max turns: 25
```

**Task**: Create Linear epic "Workflow Kill & Management System" with 6 specific issues:
1. Emergency Kill Implementation (URGENT)
2. Process Tracking Database (HIGH) 
3. Timeout Detection System (HIGH)
4. Graceful Shutdown Phases (MEDIUM)
5. Resource Cleanup Manager (MEDIUM)
6. Kill Permissions & Audit (MEDIUM)

**Expected Duration**: 15-20 minutes
**Key Deliverable**: Linear epic URL and issue IDs for BUILDER to reference

---

### 2. BUILDER - Core Implementation (AFTER LINA)
```bash  
# Manual spawn command:
# Workflow: builder
# Session: workflow_kill_implementation
# Branch: feature/workflow-kill-system  
# Max turns: 50
```

**Task**: Implement emergency kill functionality and process tracking:
- `kill_workflow()` MCP function
- Process tracking database table
- Integration with CLIExecutor
- Emergency termination of stuck workflows (run_5fbae44ab6f0, run_0dcbc991c0d4)

**Expected Duration**: 45-60 minutes
**Key Deliverable**: Functioning kill system that can terminate stuck workflows

---

### 3. GUARDIAN - Safety & Monitoring (AFTER BUILDER)
```bash
# Manual spawn command:
# Workflow: guardian  
# Session: workflow_kill_safety_validation
# Branch: feature/workflow-kill-system
# Max turns: 35
```

**Task**: Validate safety and implement monitoring:
- Safety validation test suite
- Timeout detection (auto-kill >30min initialization)
- Permission system validation
- Resource cleanup verification
- Monitoring dashboard

**Expected Duration**: 30-40 minutes
**Key Deliverable**: Complete safety validation and timeout detection system

---

## COORDINATION REQUIREMENTS

### Context Sharing
All tasks reference: `/home/namastex/workspace/am-agents-labs/docs/development/workflow-kill-system/`

### Task Dependencies
- **LINA → BUILDER**: Linear issues provide implementation requirements
- **BUILDER → GUARDIAN**: Implementation must exist before safety validation
- **All → Documentation**: Shared progress tracking in epic folder

### Communication Protocol
Each manual spawn should:
1. Read context from epic folder before starting
2. Update progress in shared documentation
3. Create handoff documentation for next task
4. Include detailed MEMORY_EXTRACTION for automation learning

---

## SUCCESS CRITERIA CHECKLIST

### After LINA (Linear Epic)
- [ ] Epic "Workflow Kill & Management System" created
- [ ] 6 issues created with proper priorities and labels
- [ ] Team notifications sent (Felipe, Cezar subscribed)
- [ ] Epic URL available for BUILDER reference

### After BUILDER (Implementation)
- [ ] `run_5fbae44ab6f0` successfully killed and cleaned up
- [ ] `run_0dcbc991c0d4` successfully killed and cleaned up  
- [ ] New workflows can be killed via MCP function
- [ ] Process tracking database operational
- [ ] No orphaned processes or zombie workflows

### After GUARDIAN (Safety & Monitoring)
- [ ] All safety validation tests pass
- [ ] Timeout detection prevents >30min initialization loops
- [ ] Permission system validated and secure
- [ ] Resource cleanup verification complete
- [ ] Monitoring dashboard functional
- [ ] System resource consumption normalized

---

## TECHNICAL IMPLEMENTATION NOTES

### Key Files to Modify (BUILDER)
- MCP automagik-workflows server (kill function)
- ClaudeCLIExecutor (process tracking)
- Database schema (workflow_processes table)
- API endpoints (kill routes)

### Safety Considerations (GUARDIAN)
- Git operations: 30s grace period
- Database transactions: 15s grace period  
- File operations: 10s grace period
- Process tree cleanup validation
- Resource leak detection

### Monitoring Requirements (GUARDIAN)
- Background stuck workflow detection
- Auto-kill workflows stuck >30min in initialization
- Real-time workflow health dashboard
- Kill operation audit trail

---

## ROLLBACK PLAN

If any task fails:
1. **LINA Failure**: Create Linear issues manually via UI
2. **BUILDER Failure**: Use system-level `kill` commands on stuck processes
3. **GUARDIAN Failure**: Implement basic timeout detection manually

**Emergency Process Kill** (if needed immediately):
```bash
# Find stuck workflow processes:
ps aux | grep claude | grep -v grep

# Kill specific process:
kill -TERM <pid>  # Wait 10 seconds
kill -KILL <pid>  # If still running
```

---

## POST-IMPLEMENTATION VALIDATION

### Immediate Validation (After All Tasks)
1. Verify stuck workflows terminated: `ps aux | grep run_5fbae44ab6f0`
2. Test new workflow kill: Start test workflow → Kill via MCP → Verify cleanup
3. Validate timeout detection: Monitor for workflows stuck >30min
4. Check resource usage: System load normalized

### Long-term Success Metrics
- Zero workflows stuck >30min in initialization
- <5 second average kill time
- 100% resource cleanup success rate
- Complete audit trail for all kills

---

## MEMORY EXTRACTION FOR AUTOMATION

This manual execution will provide critical learnings for future automated workflow orchestration:

### Pattern Recognition
- Optimal task sequencing for multi-agent systems
- Context sharing strategies between workflows
- Dependency management in distributed implementations

### Implementation Strategies  
- Emergency response workflows (kill systems, safety validators)
- Cross-workflow communication patterns
- Documentation handoff procedures

### Quality Assurance
- Safety validation approaches for critical systems
- Resource cleanup verification techniques
- Monitoring integration patterns

### Team Coordination
- Crisis response coordination (LINA → BUILDER → GUARDIAN)
- Manual fallback procedures when automation fails
- Real-time progress tracking and communication

This coordination guide ensures smooth manual execution while capturing comprehensive learnings for future automated workflow orchestration improvements.