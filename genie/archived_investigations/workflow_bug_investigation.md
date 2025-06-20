# Workflow Execution Bug Investigation

## Date: 2025-06-20

## Summary
Critical bug preventing workflow execution. API returns success but workflows don't actually start.

## UPDATE: ROOT CAUSE IDENTIFIED AND RESOLVED

### Root Cause
The workflow queue manager was disabled in the configuration:
```
- Workflow queue manager disabled (USE_WORKFLOW_QUEUE=false)
```

### Resolution
After server restart with `make restart`, workflows are now executing properly. The system was configured to queue workflows but the queue processor was disabled.

## Investigation Steps Performed

### 1. Old Docs Cleanup
- Archived all previous investigation documents to `/genie/archived_investigations/`
- Cleared test files from `/genie/`

### 2. System Status Check
- Service is running on port 8881 (local-process mode)
- Database has 2 stuck workflows from earlier (ee2630fb, 9cb7e8a9)
- Previous fixes partially applied but not working

### 3. API Testing
- Endpoint: `POST /api/v1/workflows/claude-code/run/{workflow_name}`
- API correctly creates workflow_run record in database
- Returns run_id and "pending" status
- No errors in API response

### 4. Workflow Deployment Test
- Deployed builder workflow with run_id: 6a0fecf3-523e-426f-ad37-3b228573de57
- Database shows status "running"
- No actual process starts
- No worktree created

## Key Findings

### 🔴 Critical Issues

1. **Silent Failure After API Return**
   - API returns success with run_id
   - Database record created with "running" status
   - Background task (`execute_workflow_with_isolation`) appears to fail silently
   - No error logging or status update

2. **Worktree Not Created**
   - Expected location: `/home/namastex/workspace/am-agents-labs/worktrees/{session_name}`
   - Existing persistent worktrees present (builder_persistent, surgeon_persistent, surgeon_fix_workspace)
   - New workflows not creating worktrees

3. **No Process Execution**
   - `ps aux` shows no process for our workflow
   - No logs generated in system logs
   - Workflow appears to die immediately after asyncio.create_task()

### 🟡 Partially Fixed Issues

1. **Subprocess Python Path** - Fixed in execution_isolator.py
2. **Workspace Path Storage** - Code added but still NULL in DB

### 🟢 Working Components

1. **API Layer** - Correctly processes requests and creates DB records
2. **Database** - workflow_runs table properly populated
3. **Existing Worktrees** - 3 persistent worktrees from previous runs still intact

## Code Analysis Points

### API Route (claude_code_routes.py)
- Line 387-428: `execute_workflow_with_isolation` async function
- Uses `asyncio.create_task()` to spawn background execution
- Sets environment variable `BYPASS_TASKGROUP_DETECTION`
- Updates workflow status to "running" before executing

### Potential Issues
1. Background task might be failing due to asyncio context issues
2. Environment variables not properly passed to subprocess
3. Git worktree creation failing silently
4. SDK executor not properly initialized

## Surgeon Workflow Deployed
- Run ID: 9daf1c45-f64b-4f57-9b9f-c11828ac6c01
- Session: fix_workflow_execution_bug
- Task: Fix the execution flow to ensure workflows actually start

## Verification Tests

### Test 1: Builder Workflow Execution
- Run ID: `0f32f37a-63f1-43b3-91e5-760185c4be0d`
- Claude Session ID: `80ce393a-c362-4a6d-a7e4-de8f0f1b9212`
- Result: ✅ Successfully created `/home/namastex/workspace/am-agents-labs/genie/workflow_test.py`
- The file contains proper debug logging and prints "Workflow system is working!"

### Key Learnings

1. **Configuration Mismatch**: The system was configured to use a workflow queue but the queue processor was disabled
2. **Silent Failure**: When queue is disabled, workflows are submitted but never processed
3. **Restart Required**: A server restart was needed to properly initialize the workflow processing system
4. **Monitoring**: Check logs for "Workflow queue manager disabled" message to catch this issue

## Recommendations

1. **Environment Variable**: Consider setting `USE_WORKFLOW_QUEUE=true` in production
2. **Health Check**: Add health check to verify workflow processor is running
3. **Error Handling**: Improve error messages when queue is disabled but workflows are submitted
4. **Documentation**: Update deployment docs to clarify workflow queue configuration