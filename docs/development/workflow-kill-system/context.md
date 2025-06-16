# Workflow Kill System - Context & Architecture

## Crisis Situation Summary

**CRITICAL SYSTEM STATE**: Multiple workflows stuck in initialization loops consuming resources

### Active Stuck Workflows
- `run_5fbae44ab6f0` (BUILDER) - 40+ minutes, 0% progress, initialization phase
- `run_0dcbc991c0d4` (LINA) - 2+ days, 0 turns, initialization phase
- 7+ historical workflows with same initialization loop pattern

### Root Cause Analysis
**File System Heavy Workflows Get Stuck**:
- Pattern: File operations (Read, Write, Glob, Grep, Bash) → Infinite initialization loops
- Success: API operations (Linear APIs) → Normal completion  
- Cache efficiency: 93.6% indicates repetitive processing
- Zero turn progression: Never complete initialization phase

## Current System Architecture

### Workflow Execution Flow
```
User Request → API → LocalExecutor → CLIExecutor → subprocess.Popen(claude) → Child Processes
```

### Critical Gap Identified
**❌ NO EXISTING KILL FUNCTIONALITY**:
- No `kill_workflow` MCP function
- No termination endpoints in API  
- No process management for stuck workflows
- No timeout detection system

### Available vs Missing MCP Functions
```yaml
Current Functions:
  - run_workflow ✅
  - list_workflows ✅
  - list_recent_runs ✅
  - get_workflow_status ✅

Missing Critical Functions:
  - kill_workflow ❌
  - restart_workflow ❌
  - force_terminate ❌
  - get_workflow_logs ❌
  - emergency_cleanup ❌
```

## Proposed Kill System Architecture

### 1. Core Kill API Design
```python
async def kill_workflow(run_id: str, force: bool = False) -> dict:
    """
    Terminate workflow with graceful shutdown phases:
    Phase 1: Graceful (SIGTERM) - 5 seconds
    Phase 2: Force (SIGKILL) - 10 seconds  
    Phase 3: Resource cleanup - 15 seconds
    """

async def emergency_kill(run_id: str) -> dict:
    """Immediate termination for stuck workflows"""

async def get_workflow_process_info(run_id: str) -> dict:
    """Get process information for debugging"""
```

### 2. Process Tracking Enhancement
```python
class WorkflowProcessTracker:
    def __init__(self):
        self.active_processes = {}  # run_id -> ProcessInfo
        
    def track_process(self, run_id, pid, workspace_path):
        self.active_processes[run_id] = {
            'pid': pid,
            'start_time': time.time(),
            'workspace': workspace_path,
            'status': 'running',
            'last_heartbeat': time.time()
        }
```

### 3. Safety & Resource Cleanup
```python
class ResourceCleanupManager:
    """Ensure safe termination and resource cleanup"""
    
    CRITICAL_SECTIONS = {
        'git_operations': 30,     # seconds grace period
        'database_transactions': 15,
        'file_operations': 10,
        'api_calls': 5
    }
    
    async def safe_terminate(self, run_id, force=False):
        # 1. Check for critical sections
        # 2. Wait for safe termination point
        # 3. Clean up workspace
        # 4. Update database status
        # 5. Release resources
```

## Implementation Priority

### EMERGENCY (This Sprint)
1. **Emergency Kill Function** - Stop stuck workflows immediately
2. **Process Tracking Database** - Track active workflow processes
3. **Timeout Detection** - Auto-kill workflows stuck >30min in initialization

### HIGH PRIORITY (Next Sprint)  
1. **Graceful Shutdown Phases** - Proper termination sequence
2. **Resource Cleanup** - Workspace and process cleanup
3. **Permission System** - Who can kill which workflows

### MEDIUM PRIORITY (Following Sprint)
1. **Restart Capability** - Kill and restart workflows
2. **Advanced Monitoring** - Real-time workflow health
3. **Recovery Mechanisms** - Handle partial failures

## Team Preferences Applied

### Felipe's Security Requirements
- Explicit permission checking before kills
- Audit trail for all terminations
- Safe resource cleanup with validation
- No orphaned processes or zombie workflows

### Cezar's Architecture Principles  
- Clean separation of concerns (Kill → Cleanup → Monitor)
- Scalable process tracking system
- Robust error handling and recovery
- Performance monitoring integration

## Success Metrics

### Immediate Success
- [ ] Kill stuck `run_5fbae44ab6f0` and `run_0dcbc991c0d4`
- [ ] No new workflows stuck >30min in initialization
- [ ] Process tracking working for new workflows

### Long-term Success
- [ ] Zero stuck workflows in production
- [ ] <5 second average kill time
- [ ] 100% resource cleanup success rate
- [ ] Full audit trail for all terminations

## Context for Manual Workflow Spawning

This epic requires **urgent implementation** due to stuck workflows consuming system resources. The "fake until we make it" approach will help us:

1. **Learn optimal implementation patterns** through manual execution
2. **Validate architecture decisions** before automation
3. **Ensure safety mechanisms** work correctly
4. **Build comprehensive test cases** for future automation

Each manually spawned workflow should return detailed implementation plans and progress reports for future automation integration.