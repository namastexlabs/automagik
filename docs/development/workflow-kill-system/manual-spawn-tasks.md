# Manual Workflow Spawning Tasks - Workflow Kill System

## Overview

Due to workflow initialization loops preventing automated spawning, we'll use manual spawning to implement the workflow kill system. Each task is designed for independent execution with full tool access.

---

## TASK 1: LINA - Linear Epic Creation
**Priority: MEDIUM** | **Estimated Time: 15-20 minutes**

### Task Specification
```yaml
workflow_name: lina
session_name: workflow_kill_epic_creation
git_branch: feature/workflow-kill-system
max_turns: 25
```

### Detailed Instructions for LINA
```markdown
You are LINA, tasked with creating a comprehensive Linear epic for the Workflow Kill System implementation.

## CRITICAL CONTEXT
- Multiple workflows stuck in initialization loops (run_5fbae44ab6f0, run_0dcbc991c0d4)
- NO existing kill functionality in the platform
- System impairment affecting BUILDER workflows specifically
- Emergency implementation needed

## PRIMARY OBJECTIVE
Create a Linear epic titled "Workflow Kill & Management System" with comprehensive task breakdown.

## SPECIFIC TASKS

### 1. Linear Epic Creation
Use mcp__linear__ tools to:
- Get current viewer and team information
- Create epic: "Workflow Kill & Management System"
- Set priority: HIGH
- Add epic description with current crisis context

### 2. Issue Creation (Create these specific issues in order)
1. **Emergency Kill Implementation**
   - Title: "Implement emergency kill function for stuck workflows"
   - Priority: URGENT (1)
   - Labels: bug, critical, backend
   - Description: Immediate kill capability for run_5fbae44ab6f0 and similar stuck workflows

2. **Process Tracking Database**
   - Title: "Add workflow process tracking to database"
   - Priority: HIGH (2)
   - Labels: enhancement, database, backend
   - Description: Track PIDs and process info for kill capability

3. **Timeout Detection System**
   - Title: "Implement auto-kill for workflows stuck >30min in initialization"
   - Priority: HIGH (2)
   - Labels: enhancement, monitoring, backend
   - Description: Background monitoring and auto-termination

4. **Graceful Shutdown Phases**
   - Title: "Implement graceful shutdown with SIGTERM/SIGKILL phases"
   - Priority: MEDIUM (3)
   - Labels: enhancement, backend, safety
   - Description: Multi-phase termination with proper cleanup

5. **Resource Cleanup Manager**
   - Title: "Implement comprehensive resource cleanup after kill"
   - Priority: MEDIUM (3)
   - Labels: enhancement, cleanup, backend
   - Description: Workspace, files, processes cleanup

6. **Kill Permissions & Audit**
   - Title: "Add permission system and audit trail for workflow kills"
   - Priority: MEDIUM (3)
   - Labels: security, audit, backend
   - Description: Who can kill what + audit logging

### 3. Epic Organization
- Link all issues to the epic
- Set up project view if applicable
- Add epic to current cycle if active
- Set epic status to "In Progress"

### 4. Team Coordination
- Subscribe Felipe and Cezar to the epic
- Add comments with crisis context
- Set appropriate team assignments

## DELIVERABLES
1. Created Linear epic with proper priority and context
2. 6 specific issues created and linked to epic
3. Team notifications and assignments completed
4. Epic URL and issue IDs for tracking

## MEMORY EXTRACTION REQUIREMENTS
At the end, include a MEMORY_EXTRACTION section with:
- Linear integration patterns learned
- Epic creation best practices
- Issue breakdown strategies for technical crises
- Team coordination approaches for urgent implementations

## SUCCESS CRITERIA
- Epic is visible in Linear workspace
- All team members notified
- Clear implementation roadmap established
- Next workflows can reference Linear issues for implementation
```

---

## TASK 2: BUILDER - Kill System Implementation
**Priority: HIGH** | **Estimated Time: 45-60 minutes**

### Task Specification
```yaml
workflow_name: builder
session_name: workflow_kill_implementation
git_branch: feature/workflow-kill-system
max_turns: 50
```

### Detailed Instructions for BUILDER
```markdown
You are BUILDER, tasked with implementing the core workflow kill functionality.

## CRITICAL CONTEXT
Reference: /home/namastex/workspace/am-agents-labs/docs/development/workflow-kill-system/context.md

**EMERGENCY SITUATION**: 
- run_5fbae44ab6f0 stuck 40+ minutes (BUILDER workflow)
- run_0dcbc991c0d4 stuck 2+ days (LINA workflow)
- NO existing kill functionality
- File system workflows getting stuck in initialization loops

## PRIMARY OBJECTIVE
Implement emergency kill functionality and process tracking system.

## IMPLEMENTATION REQUIREMENTS

### 1. Emergency Kill Function (PRIORITY 1)
Implement in the MCP automagik-workflows server:

```python
async def kill_workflow(run_id: str, force: bool = False) -> dict:
    """
    Kill a running workflow with proper cleanup
    
    Args:
        run_id: Workflow run identifier
        force: If True, use SIGKILL immediately
        
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

### 2. Process Tracking Enhancement (PRIORITY 1)
Modify ClaudeCLIExecutor to track processes:

```python
class WorkflowProcessTracker:
    def __init__(self):
        self.active_processes = {}
        
    def register_process(self, run_id: str, pid: int, workspace: str):
        """Register workflow process for tracking"""
        
    def get_process_info(self, run_id: str) -> dict:
        """Get process information for kill operations"""
        
    async def emergency_kill(self, run_id: str) -> dict:
        """Emergency termination for stuck workflows"""
```

### 3. Database Schema Updates (PRIORITY 1)
Add process tracking table:

```sql
CREATE TABLE IF NOT EXISTS workflow_processes (
    run_id TEXT PRIMARY KEY,
    pid INTEGER,
    status TEXT,
    started_at TIMESTAMP,
    workspace_path TEXT,
    last_heartbeat TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 4. Integration with Existing System (PRIORITY 1)
- Integrate with LocalExecutor and CLIExecutor
- Add process registration on workflow start
- Add cleanup on workflow completion
- Handle process lookup for kill operations

### 5. Safety Mechanisms (PRIORITY 2)
```python
class SafeKillManager:
    CRITICAL_SECTIONS = {
        'git_operations': 30,     # seconds grace period
        'database_transactions': 15,
        'file_operations': 10
    }
    
    async def check_safe_to_kill(self, run_id: str) -> bool:
        """Check if workflow is in critical section"""
        
    async def wait_for_safe_kill(self, run_id: str, timeout: int = 60):
        """Wait for safe termination point"""
```

## IMMEDIATE ACTIONS REQUIRED

### Step 1: Kill Stuck Workflows
- Implement emergency kill for run_5fbae44ab6f0
- Implement emergency kill for run_0dcbc991c0d4
- Validate cleanup completed successfully

### Step 2: Prevent Future Issues  
- Add process tracking to new workflows
- Add timeout detection (30min initialization limit)
- Test kill functionality with new workflows

## FILE LOCATIONS TO MODIFY
Look for these key files:
- MCP automagik-workflows server code
- Workflow executor classes (LocalExecutor, CLIExecutor)
- Database schema/migration files
- API endpoints for workflow management

## TESTING REQUIREMENTS
1. **Emergency Kill Test**: Kill currently stuck workflows
2. **New Workflow Test**: Start and kill a new workflow
3. **Cleanup Validation**: Ensure no orphaned processes
4. **Database Consistency**: Verify tracking data accuracy

## DELIVERABLES
1. Emergency kill function implemented and tested
2. Process tracking system active
3. Stuck workflows killed and cleaned up
4. Database schema updated
5. Integration tests passing
6. Documentation for new kill functionality

## MEMORY EXTRACTION REQUIREMENTS
Include detailed MEMORY_EXTRACTION section with:
- Workflow kill implementation patterns
- Process tracking best practices
- Emergency termination safety considerations
- Integration patterns with existing workflow system
- Testing strategies for kill functionality

## SUCCESS CRITERIA
- run_5fbae44ab6f0 and run_0dcbc991c0d4 successfully terminated
- New workflows can be killed successfully
- No orphaned processes or zombie workflows
- System resource consumption normalized
- Kill functionality available via MCP
```

---

## TASK 3: GUARDIAN - Safety Validation & Monitoring
**Priority: MEDIUM** | **Estimated Time: 30-40 minutes**

### Task Specification
```yaml
workflow_name: guardian
session_name: workflow_kill_safety_validation
git_branch: feature/workflow-kill-system
max_turns: 35
```

### Detailed Instructions for GUARDIAN
```markdown
You are GUARDIAN, responsible for validating the safety and reliability of the workflow kill system.

## CRITICAL CONTEXT
The workflow kill system has been implemented by BUILDER. Your role is to ensure it's safe, secure, and reliable.

## PRIMARY OBJECTIVE
Validate kill system safety, implement timeout detection, and create monitoring capabilities.

## VALIDATION REQUIREMENTS

### 1. Safety Validation (PRIORITY 1)
Test and validate:

```python
# Test scenarios to validate:
SAFETY_TESTS = [
    "kill_during_git_operation",
    "kill_during_file_write", 
    "kill_during_database_transaction",
    "kill_with_active_api_calls",
    "kill_with_child_processes",
    "kill_non_existent_workflow",
    "kill_already_completed_workflow",
    "kill_without_permissions"
]
```

### 2. Timeout Detection Implementation (PRIORITY 1)
```python
class WorkflowTimeoutMonitor:
    def __init__(self):
        self.initialization_timeout = 300  # 5 minutes
        self.total_timeout = 3600         # 1 hour
        
    async def monitor_workflows(self):
        """Background task to detect stuck workflows"""
        
    async def auto_kill_stuck_workflows(self):
        """Automatically kill workflows stuck in initialization"""
        
    def is_stuck_in_initialization(self, workflow_info: dict) -> bool:
        """Detect initialization loops"""
```

### 3. Permission System Validation (PRIORITY 2)
```python
class WorkflowKillPermissions:
    def __init__(self):
        self.permissions = {
            'owner': ['kill_own', 'kill_force'],
            'admin': ['kill_any', 'kill_force', 'emergency_kill'],
            'team_lead': ['kill_team_workflows'],
            'readonly': []
        }
        
    def can_kill_workflow(self, user_id: str, workflow_id: str, force: bool = False) -> bool:
        """Validate kill permissions"""
```

### 4. Resource Cleanup Validation (PRIORITY 1)
Ensure complete cleanup after kills:
- Process termination validation
- Workspace directory cleanup
- Database state consistency
- Temporary file removal
- Memory leak detection

### 5. Monitoring Dashboard Creation (PRIORITY 2)
Create monitoring capabilities:
- Active workflow health status
- Kill operation audit trail
- Resource usage tracking
- Stuck workflow detection alerts

## TESTING SCENARIOS

### Critical Safety Tests
1. **Git Operation Safety**: Kill during git commit/push
2. **Database Transaction Safety**: Kill during DB writes
3. **File System Safety**: Kill during file operations
4. **Process Tree Cleanup**: Ensure all child processes killed
5. **Resource Leak Detection**: No orphaned resources

### Performance Tests  
1. **Kill Speed**: <5 seconds for graceful kill
2. **Force Kill Speed**: <2 seconds for force kill
3. **Cleanup Speed**: <10 seconds for full cleanup
4. **Monitoring Overhead**: <5% CPU usage for monitoring

### Edge Case Tests
1. **Rapid Kill Requests**: Multiple kill requests for same workflow
2. **Network Disconnection**: Kill during network operations
3. **Disk Full Scenarios**: Kill when disk space exhausted
4. **Memory Pressure**: Kill under high memory usage

## IMPLEMENTATION DELIVERABLES

### 1. Timeout Detection System
```python
# Background service that monitors workflow health
async def workflow_health_monitor():
    while True:
        stuck_workflows = await detect_stuck_workflows()
        for workflow in stuck_workflows:
            await auto_kill_workflow(workflow.run_id)
        await asyncio.sleep(60)  # Check every minute
```

### 2. Safety Validation Suite
Complete test suite validating all safety scenarios with automated tests.

### 3. Permission Framework
Role-based permission system for workflow kill operations.

### 4. Audit Trail System
```python
# Complete audit logging for all kill operations
class KillAuditLogger:
    def log_kill_attempt(self, run_id, user_id, reason, success):
        """Log all kill attempts for security audit"""
```

### 5. Monitoring Integration
Real-time dashboard showing:
- Active workflow health
- Recent kill operations  
- System resource usage
- Alert notifications for stuck workflows

## DELIVERABLES
1. Complete safety validation test suite
2. Timeout detection system implemented
3. Permission framework validated
4. Resource cleanup validation completed
5. Monitoring dashboard functional
6. Audit trail system active
7. All edge cases tested and handled

## MEMORY_EXTRACTION REQUIREMENTS
Document learnings about:
- Workflow safety validation patterns
- Timeout detection strategies
- Permission system design for workflow operations
- Resource cleanup verification techniques
- Monitoring and alerting best practices for workflow systems

## SUCCESS CRITERIA
- All safety tests pass with 100% success rate
- Timeout detection prevents workflows stuck >5min in initialization
- Permission system prevents unauthorized kills
- Complete resource cleanup verified
- Monitoring system provides real-time visibility
- Audit trail captures all operations
```

---

## COORDINATION INSTRUCTIONS

### Manual Spawning Process
1. **LINA First**: Create Linear epic and issues for tracking
2. **BUILDER Second**: Implement core kill functionality 
3. **GUARDIAN Third**: Validate safety and add monitoring

### Inter-Task Communication
- Each task should reference `/home/namastex/workspace/am-agents-labs/docs/development/workflow-kill-system/`
- BUILDER should reference Linear issues created by LINA
- GUARDIAN should test implementations created by BUILDER
- All tasks should update progress in shared documentation

### Reporting Requirements
Each manually spawned workflow should:
1. Create detailed progress reports in the epic folder
2. Include MEMORY_EXTRACTION sections for future automation
3. Document any issues or blockers encountered
4. Provide clear handoff information for next tasks

### Success Validation
After all manual spawns complete:
- [ ] Stuck workflows (run_5fbae44ab6f0, run_0dcbc991c0d4) terminated
- [ ] New workflows can be killed successfully  
- [ ] Timeout detection prevents future stuck workflows
- [ ] Complete safety validation passes
- [ ] Linear epic reflects implementation progress
- [ ] Documentation complete for future automation

This manual approach will provide the implementation needed while the workflow initialization bug is being resolved, and generate comprehensive learnings for future automated workflow orchestration.