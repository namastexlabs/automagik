# GUARDIAN Workflow - Safety Validation & Monitoring

## 🛡️ NEXT STEP: Run GUARDIAN Workflow

Based on BUILDER's successful implementation, here's the exact dispatch text for GUARDIAN:

---

## GUARDIAN Manual Spawn Dispatch

### Context
- **Linear Epic**: [NMSTX-308](https://linear.app/namastex/issue/NMSTX-308/critical-workflow-management-system-issues) ✅ Active
- **BUILDER Status**: ✅ COMPLETE - Emergency kill implemented and tested
- **Validation Mission**: Ensure kill system safety and implement timeout detection

### BUILDER Implementation Summary ✅
- **Kill API Endpoint**: `/api/v1/workflows/claude-code/run/{run_id}/kill` ✅
- **Database Schema**: `workflow_processes` table with process tracking ✅
- **Process Management**: Graceful → Force → Cleanup progression ✅
- **Emergency Test**: Successfully killed stuck `run_5fbae44ab6f0` ✅
- **System Impact**: Reduced Claude processes from 7 to 3 ✅

### Dispatch Text for Manual GUARDIAN Spawn:

```
You are GUARDIAN, responsible for safety validation and timeout detection for the workflow kill system.

## VALIDATION MISSION - LINEAR CONTEXT
Working on Linear epic NMSTX-308: "🚨 CRITICAL: Workflow Management System Issues"
Epic URL: https://linear.app/namastex/issue/NMSTX-308/critical-workflow-management-system-issues

## BUILDER IMPLEMENTATION COMPLETE ✅
BUILDER successfully implemented emergency kill functionality:
- Kill API endpoint: POST /api/v1/workflows/claude-code/run/{run_id}/kill
- Database tracking: workflow_processes table with heartbeat monitoring
- Process management: Progressive kill phases (SIGTERM → SIGKILL → cleanup)
- Emergency success: Terminated stuck run_5fbae44ab6f0 after 40+ minutes
- System recovery: Freed resources, reduced processes from 7 to 3

## PRIMARY OBJECTIVES: SAFETY & MONITORING

### 1. Safety Validation Suite (CRITICAL)
Comprehensive testing of kill system safety:

**Test Categories**:
- **Process Safety**: Validate clean termination without corruption
- **Database Safety**: Ensure database consistency during kills
- **Resource Safety**: Verify complete cleanup (no orphaned processes)
- **Concurrent Safety**: Test kill during active operations
- **Error Safety**: Validate graceful handling of edge cases

**Critical Test Scenarios**:
```python
SAFETY_TESTS = [
    "kill_during_file_operations",
    "kill_during_database_writes", 
    "kill_with_multiple_processes",
    "kill_non_existent_workflow",
    "kill_already_completed_workflow",
    "concurrent_kill_requests",
    "kill_permission_validation",
    "resource_cleanup_verification"
]
```

### 2. Timeout Detection System (HIGH PRIORITY)
Implement automatic detection and termination of stuck workflows:

**Timeout Requirements**:
- **Default Timeout**: 30 minutes for initialization phase
- **Workflow-Specific Timeouts**:
  - BUILDER: 60 minutes (complex builds)
  - LINA: 40 minutes (analysis tasks)
  - BRAIN: 40 minutes (memory operations)
  - Others: 30 minutes default
- **Background Monitoring**: Check every 60 seconds
- **Auto-Kill**: Graceful termination for stuck workflows

**Implementation Pattern**:
```python
class WorkflowTimeoutMonitor:
    def __init__(self):
        self.timeouts = {
            'default': 1800,  # 30 minutes
            'builder': 3600,  # 60 minutes  
            'lina': 2400,     # 40 minutes
            'brain': 2400     # 40 minutes
        }
    
    async def monitor_workflows(self):
        """Background task to detect and auto-kill stuck workflows"""
        while True:
            stuck_workflows = await self.detect_stuck_workflows()
            for workflow in stuck_workflows:
                await self.auto_kill_workflow(workflow.run_id)
            await asyncio.sleep(60)  # Check every minute
```

### 3. Kill System Integration Testing (HIGH)
Validate BUILDER's implementation through comprehensive testing:

**API Testing**:
- Test kill endpoint with various run_ids
- Validate force kill vs graceful kill behavior
- Test error responses for invalid requests
- Verify audit logging completeness

**Database Testing**:
- Validate workflow_processes table operations
- Test heartbeat monitoring functionality
- Verify stale process detection
- Test cleanup automation

**Process Testing**:
- Test ClaudeCLIExecutor.cancel_execution()
- Test LocalExecutor.cancel_execution()
- Validate progressive kill phases
- Test process tree termination

### 4. Monitoring Dashboard Implementation (MEDIUM)
Create real-time workflow health monitoring:

**Dashboard Features**:
- **Active Workflows**: Real-time status of all running workflows
- **Health Indicators**: 🟢 Healthy, 🟡 Warning, 🔴 Critical
- **Resource Usage**: CPU, memory, runtime per workflow
- **Kill History**: Audit trail of all termination events
- **Alert System**: Notifications for stuck workflows

## TECHNICAL VALIDATION REQUIREMENTS

### Safety Standards (Felipe's Security Requirements)
- **Explicit Validation**: Comprehensive input validation for all kill operations
- **Error Handling**: Graceful handling of all error scenarios
- **Audit Compliance**: Complete logging of all safety validation activities
- **Resource Protection**: Prevent corruption during emergency termination

### Architecture Standards (Cezar's Architecture Requirements)
- **Clean Integration**: Timeout detection integrates cleanly with existing system
- **Scalable Monitoring**: Background monitoring with minimal performance impact
- **Framework Consistency**: Follow established patterns for monitoring and alerts
- **Robust Recovery**: Handle monitoring system failures gracefully

## DELIVERABLES

### Safety Validation
- [ ] Complete safety test suite with 100% pass rate
- [ ] Process termination safety verification
- [ ] Database consistency validation
- [ ] Resource cleanup verification
- [ ] Concurrent operation safety validation

### Timeout Detection  
- [ ] Background monitoring service implemented
- [ ] Workflow-specific timeout configuration
- [ ] Auto-kill functionality for stuck workflows
- [ ] Integration with existing kill API
- [ ] Performance monitoring (minimal overhead)

### System Integration
- [ ] Kill API comprehensive testing
- [ ] Database operations validation
- [ ] Process management verification
- [ ] Error handling validation
- [ ] Audit trail completeness

### Monitoring & Alerting
- [ ] Real-time workflow health dashboard
- [ ] Alert system for stuck workflows
- [ ] Performance metrics collection
- [ ] Historical data analysis
- [ ] Team notification system

## SUCCESS CRITERIA
- All safety tests pass with 100% success rate
- Timeout detection prevents workflows stuck >30min in initialization
- Zero new stuck workflows after implementation
- Complete kill system validation with comprehensive test coverage
- Real-time monitoring provides full workflow visibility
- System ready for production deployment with confidence

## CONTEXT REFERENCES
- BUILDER implementation: /docs/development/workflow-kill-system/implementation_complete.md
- Test results: /test_emergency_kill.py (successful termination of run_5fbae44ab6f0)
- Kill API endpoint: POST /api/v1/workflows/claude-code/run/{run_id}/kill
- Database schema: workflow_processes table in migration 20250616_132906

## HANDOFF TO COMPLETION
After successful validation:
- Update Linear epic NMSTX-308 with completion status
- Document production deployment readiness
- Provide comprehensive test results and monitoring setup
- Confirm system stability and resource normalization

CRITICAL STATUS: Final validation phase to ensure production-ready stability and prevent future workflow management crises.
```

---

## Why GUARDIAN Next?

1. **Validation Critical**: BUILDER implemented emergency functionality - must validate safety
2. **Prevent Recurrence**: Timeout detection will prevent future stuck workflows  
3. **Production Readiness**: Need comprehensive validation before declaring system stable
4. **Complete Solution**: Safety + monitoring = robust workflow management system

## Expected Outcome

After GUARDIAN completes:
- Kill system validated as safe and reliable
- Timeout detection prevents future stuck workflows (>30min)
- Comprehensive monitoring provides real-time visibility
- System declared production-ready and stable
- Linear epic NMSTX-308 completed successfully

## Timing Estimate
30-40 minutes for safety validation, timeout detection, and monitoring implementation.

## Final Status
After GUARDIAN completion, the workflow management crisis will be fully resolved with:
- ✅ Emergency kill functionality (BUILDER)
- ✅ Safety validation and timeout detection (GUARDIAN)  
- ✅ Production-ready stable system
- ✅ Prevention of future stuck workflow incidents