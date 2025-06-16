# Manual Workflow Dispatch Texts - Workflow Kill System

Based on existing Linear epic **NMSTX-300** and completed analysis, here are the exact dispatch texts for manual spawning:

---

## TASK 1: LINA - Update Existing Epic
**Linear Reference**: [NMSTX-300](https://linear.app/namastex/issue/NMSTX-300/workflow-lifecycle-management-and-kill-functionality) (already exists)

### Dispatch Text for LINA
```
You are LINA, responsible for Linear workspace management and epic coordination.

## CONTEXT - EXISTING WORK
Epic NMSTX-300 "🚨 Workflow Lifecycle Management & Kill Functionality" already exists with 6 subtasks:
- NMSTX-301: Implement workflow kill functionality in MCP server ⏳
- NMSTX-302: Add timeout detection for stuck initialization ⏳  
- NMSTX-303: Create workflow restart capability ⏳
- NMSTX-304: Fix initialization loop bug affecting all workflows ⏳
- NMSTX-305: Add workflow health monitoring dashboard ⏳
- NMSTX-306: Test kill functionality with current stuck workflows ⏳

## URGENT TASK
1. **Update Epic Status**: Change NMSTX-300 from "Triage" to "In Progress"
2. **Prioritize Implementation**: Update NMSTX-301 (kill functionality) to highest priority
3. **Add Implementation Notes**: Comment on NMSTX-301 with emergency kill requirements for:
   - run_5fbae44ab6f0 (BUILDER - stuck 40+ minutes)
   - run_0dcbc991c0d4 (LINA - stuck 2+ days)
4. **Team Coordination**: Subscribe Felipe and Cezar to critical issues
5. **Progress Tracking**: Add comments linking to manual implementation approach

## DELIVERABLES
- Epic status updated to "In Progress"
- NMSTX-301 prioritized and detailed for emergency implementation
- Team notifications sent
- Manual implementation approach documented in epic comments

## SUCCESS CRITERIA
- Clear implementation roadmap established in Linear
- Team aligned on emergency approach
- Next workflows have clear Linear issue references
```

---

## TASK 2: BUILDER - Emergency Kill Implementation
**Linear Reference**: [NMSTX-301](https://linear.app/namastex/issue/NMSTX-301/implement-workflow-kill-functionality-in-mcp-server)

### Dispatch Text for BUILDER
```
You are BUILDER, tasked with implementing the emergency workflow kill functionality.

## CONTEXT - LINEAR INTEGRATION
Working on Linear issue NMSTX-301: "🔪 Implement workflow kill functionality in MCP server"
Epic: NMSTX-300 "🚨 Workflow Lifecycle Management & Kill Functionality"

## CRITICAL EMERGENCY SITUATION
Multiple workflows stuck consuming resources:
- run_5fbae44ab6f0 (BUILDER) - 40+ minutes stuck in initialization
- run_0dcbc991c0d4 (LINA) - 2+ days stuck in initialization  
- 7+ additional workflows in initialization loops

## PRIMARY OBJECTIVES (from NMSTX-301)
1. **Emergency Kill Function**: Implement `mcp__automagik_workflows__kill_workflow(run_id)` 
2. **Three Kill Levels**: 
   - Graceful shutdown (SIGTERM + cleanup)
   - Forced shutdown (immediate termination)
   - System kill (OS-level process termination)
3. **Process Tracking**: Add workflow process tracking to database
4. **Immediate Action**: Kill stuck workflows run_5fbae44ab6f0 and run_0dcbc991c0d4

## TECHNICAL REQUIREMENTS
Based on comprehensive analysis in `/docs/development/workflow-kill-system/`:
- Modify MCP automagik-workflows server to expose kill_workflow API
- Add workflow process tracking database table
- Integrate with LocalExecutor/CLIExecutor for process management
- Implement safety mechanisms for critical sections (git, DB transactions)
- Add audit trail for all kill operations

## IMPLEMENTATION SEQUENCE
1. **Emergency Kill**: Implement basic kill for stuck workflows immediately
2. **Process Tracking**: Add database schema for workflow process tracking  
3. **Safety Systems**: Add graceful shutdown phases and resource cleanup
4. **Integration**: Connect with existing workflow execution pipeline
5. **Testing**: Validate kill functionality with stuck workflows

## DELIVERABLES
- Emergency kill function implemented and working
- Stuck workflows (run_5fbae44ab6f0, run_0dcbc991c0d4) terminated
- Process tracking system operational
- NMSTX-301 marked as completed in Linear
- Handoff documentation for GUARDIAN validation

## SUCCESS CRITERIA
- All stuck workflows successfully killed and cleaned up
- No orphaned processes or zombie workflows  
- New workflows can be killed via MCP
- System resource consumption normalized
- Zero regression in existing workflow functionality
```

---

## TASK 3: GUARDIAN - Safety Validation & Monitoring  
**Linear Reference**: [NMSTX-302](https://linear.app/namastex/issue/NMSTX-302/add-timeout-detection-for-stuck-initialization) + [NMSTX-306](https://linear.app/namastex/issue/NMSTX-306/test-kill-functionality-with-current-stuck-workflows)

### Dispatch Text for GUARDIAN
```
You are GUARDIAN, responsible for safety validation and timeout detection for the workflow kill system.

## CONTEXT - LINEAR INTEGRATION
Working on multiple Linear issues:
- NMSTX-302: "⏰ Add timeout detection for stuck initialization" 
- NMSTX-306: "🧪 Test kill functionality with current stuck workflows"
Epic: NMSTX-300 "🚨 Workflow Lifecycle Management & Kill Functionality"

## CRITICAL VALIDATION MISSION
BUILDER has implemented emergency kill functionality. Your role is to:
1. **Validate Safety**: Ensure kill system doesn't corrupt workflows or data
2. **Implement Timeout Detection**: Auto-kill workflows stuck >30min in initialization
3. **Test Emergency Scenarios**: Validate kill functionality works on real stuck workflows

## PRIMARY OBJECTIVES (from NMSTX-302 & NMSTX-306)

### Timeout Detection Implementation (NMSTX-302)
- Auto-kill workflows stuck >30min in initialization phase
- Configurable timeout thresholds per workflow type:
  - Default: 30 minutes  
  - BUILDER: 60 minutes (complex builds)
  - LINA: 40 minutes (analysis tasks)
  - BRAIN: 40 minutes (complex tasks)
- Background monitoring service to detect stuck workflows

### Safety Validation & Testing (NMSTX-306)
Test scenarios with 7+ identified stuck workflows:
- LINA-11ae8a62, LINA-3df6054e, LINA-8e9c6cd6 (30+ min stuck)
- BUILDER-2c103bc4, BRAIN-03eadac0, TEST-2cf956de, ARCHITECT-78de48e4

## TECHNICAL IMPLEMENTATION
1. **Safety Validation Suite**:
   - Test kill during git operations (30s grace period)
   - Test kill during file operations (10s grace period)  
   - Test kill during database transactions (15s grace period)
   - Validate complete resource cleanup

2. **Timeout Detection System**:
   ```python
   class WorkflowTimeoutMonitor:
       def __init__(self):
           self.initialization_timeout = 1800  # 30 minutes
           self.monitoring_interval = 60       # 1 minute checks
       
       async def monitor_stuck_workflows(self):
           # Auto-kill workflows stuck in initialization >30min
   ```

3. **Comprehensive Testing**:
   - Test all three kill phases (graceful → forced → system)
   - Validate no orphaned processes remain
   - Test permission system prevents unauthorized kills
   - Verify audit trail captures all operations

## DELIVERABLES
- Complete safety validation test suite passing
- Timeout detection system implemented and active
- All 7+ stuck workflows tested and validated for kill capability
- NMSTX-302 and NMSTX-306 marked completed in Linear
- Monitoring dashboard functional
- Comprehensive test report for production deployment

## SUCCESS CRITERIA  
- Zero workflows stuck >30min in initialization going forward
- 100% successful kill rate with complete cleanup
- All safety tests pass (git, file, database operations)
- Real-time monitoring provides workflow health visibility
- Complete audit trail for security compliance
- System ready for production deployment
```

---

## Coordination Notes

### Existing Linear Context
- **Epic NMSTX-300** already created with comprehensive scope
- **6 subtasks** already defined with proper priorities
- **Team assignments** already configured (Felipe, Cezar)
- **GitHub integration** already set up for issue tracking

### Manual Spawn Sequence
1. **LINA**: Update existing epic status and prioritization (10-15 min)
2. **BUILDER**: Implement emergency kill functionality (45-60 min)  
3. **GUARDIAN**: Validate safety and implement monitoring (30-40 min)

### Key Changes from Original Plan
- **Leverage existing Linear work** instead of creating duplicate epic
- **Focus on emergency implementation** of NMSTX-301 kill functionality
- **Coordinate with existing issue assignments** (Felipe/Cezar already involved)
- **Reference established GitHub integration** for tracking

### Success Validation
- All tasks reference existing Linear issues for tracking
- Implementation aligns with already-established requirements  
- Team coordination builds on existing epic structure
- Progress updates flow through established Linear→GitHub integration

This approach ensures we build on LINA's previous excellent work while addressing the immediate crisis with stuck workflows.