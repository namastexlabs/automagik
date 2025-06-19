# 🚨 **CRITICAL WORKFLOW SYSTEM BUG REPORT**

## **Executive Summary**

During comprehensive QA testing, we discovered **two critical bugs** in the workflow execution system:

1. **TaskGroup Conflict Bug**: Complex workflows fail with TaskGroup errors despite actually executing work
2. **Status Reporting Bug**: Execution metrics are not properly synchronized between logs and database/API

**Impact**: Production workflows appear to fail/incomplete while actually succeeding, leading to incorrect monitoring and potential duplicate work.

## **Bug #1: TaskGroup Conflicts in Complex Workflows**

### **Symptoms**
- Complex multi-turn workflows fail with "TaskGroup error in thread pool context"
- Workflows execute substantial work (10+ turns, 5+ tools) before terminating
- Status shows "failed" despite actual implementation work being done
- Simple workflows complete successfully

### **Evidence**
```
COMPLEX TASK (FAILED):
- Log: "TaskGroup error in thread pool context (expected): unhandled errors in a TaskGroup"
- Log: "Processing 17 collected messages for data extraction"
- Log: "Correcting turn count from 0 to 10 based on actual AssistantMessages"
- Log: "5 tools captured: ['mcp__agent-memory__search_memory_nodes', 'mcp__agent-memory__search_memory_facts', 'TodoWrite', 'LS', 'Read']"
- Status: FAILED due to TaskGroup conflict

SIMPLE TASK (SUCCEEDED):
- Log: "Cost: $0.1087, Turns: 4"
- Log: "Write (id: toolu_015GQW8dh1XLjJzSkfFVnjxg)"
- File created: /hello.py with correct content
- Git commits: Auto-committed and merged successfully
```

### **Root Cause Analysis**
The TaskGroup conflicts appear related to asyncio event loop management in the SDK executor. Previous threading fixes were insufficient for complex workflows that generate multiple concurrent operations.

### **Reproduction Steps**
1. Start complex workflow: `run_workflow(workflow_name="builder", message="Complex UI enhancement task...", max_turns=15)`
2. Monitor logs for ~40 seconds
3. Observe TaskGroup error followed by premature termination
4. Check status API - shows "failed" despite substantial work completed

---

## **Bug #2: Status Reporting Data Synchronization**

### **Symptoms**
- API status endpoints show 0 tokens, 0 turns, 0 tools for successful workflows
- Database records show cost_estimate: 0, total_tokens: 0 
- Logs show correct execution metrics (e.g., "Cost: $0.1087, Turns: 4")
- Disconnect between actual execution and persisted metrics

### **Evidence**
```
EXECUTION LOGS:
✅ "SDK Executor: Captured final metrics during streaming - Cost: $0.1087, Turns: 4"
✅ "SDK Executor: Captured tool usage - Write (id: toolu_015GQW8dh1XLjJzSkfFVnjxg)"

DATABASE RECORD:
❌ cost_estimate: 0
❌ total_tokens: 0
❌ tools: 0

API STATUS:
❌ "Cost: $0.0000, Tokens: 0, Turns: 0, Tools: 0"
```

### **Root Cause Analysis**
The metrics captured during stream processing are not being properly persisted to the database. The status endpoint relies on database records rather than the actual execution logs.

### **Data Flow Issue**
```
Stream Processing → Metrics Captured → ❌ NOT SAVED → Database → API Response
                                    ↘️ Saved to Logs Only
```

---

## **Detailed Test Results**

### **Test Case 1: Simple Task (SUCCESS with Wrong Metrics)**
```
Task: "Create a simple hello world function in Python and save it to a new file called hello.py"
Run ID: 6fa6ada1-dc7e-465b-85a8-8f005518f95b

ACTUAL EXECUTION:
✅ File created: hello.py with correct content
✅ Git commits: Auto-committed and merged to main
✅ Cost incurred: $0.1087
✅ Turns executed: 4
✅ Tools used: Write

REPORTED STATUS:
❌ Status: "completed" (correct)
❌ Cost: $0.0000 (incorrect - should be $0.1087)
❌ Tokens: 0 (incorrect - should be >0)
❌ Turns: 0 (incorrect - should be 4)
❌ Tools: [] (incorrect - should include Write)
```

### **Test Case 2: Complex Task (FAILURE with Execution)**
```
Task: "Enhance the workflow dashboard UI to add real-time progress updates with websockets..."
Run ID: e18259d0-1a5d-49fb-a290-40015b4c5663

ACTUAL EXECUTION:
✅ Memory searches performed
✅ Todo planning completed  
✅ File reads executed
✅ 10 turns processed
✅ 5 tools used successfully

FAILURE POINT:
❌ TaskGroup conflict after substantial work
❌ Marked as "failed" despite successful execution
❌ No auto-commit due to "failed" status
❌ Work lost despite being completed
```

---

## **Critical Impact Assessment**

### **Production Implications**
1. **False Negatives**: Working workflows marked as failed
2. **Lost Work**: Complex implementations discarded due to TaskGroup errors
3. **Incorrect Billing**: Costs not tracked properly
4. **Monitoring Blind Spots**: Dashboards show 0 activity for active workflows
5. **Resource Waste**: Duplicate work due to appearing "incomplete"

### **User Experience Impact**
- Users see workflows as "failed" when they actually succeeded
- No visibility into actual resource consumption
- Complex tasks consistently appear to fail
- Simple tasks appear to complete without doing work

---

## **Immediate Fixes Needed**

### **Priority 1: Fix Status Reporting Data Persistence**
```python
# Problem: Metrics not saved to database
# Location: SDK Executor stream processing → database persistence
# Fix: Ensure captured metrics are written to workflow_runs table

# Current flow:
stream_metrics = capture_metrics()  # ✅ Working
# Missing: persist_metrics_to_database(stream_metrics)  # ❌ Not happening
```

### **Priority 2: Resolve TaskGroup Conflicts**
```python
# Problem: Complex workflows trigger TaskGroup errors
# Location: SDK Executor asyncio event loop management
# Investigation needed: Thread pool interaction with asyncio
```

---

## **Recommended Investigation Steps**

1. **Trace the metrics persistence path** from stream capture to database
2. **Examine TaskGroup usage** in SDK executor for complex workflows
3. **Test asyncio event loop isolation** in threading context
4. **Validate database schema** matches expected metrics fields
5. **Review transaction handling** during workflow completion

---

## **Test Environment Details**

- **Platform**: Linux WSL2
- **Database**: SQLite 
- **Workflow Mode**: Local with persistent workspaces
- **Test Time**: 2025-06-19 18:13-18:17
- **QA Procedure**: Comprehensive real-world testing

---

## **Verification Commands**

```bash
# Check actual files created
find /home/namastex/workspace/am-agents-labs -name "hello.py" -ls

# Verify git commits  
git log --oneline -5 | grep -i workflow

# Check database inconsistency
sqlite3 data/automagik_agents.db "SELECT run_id, cost_estimate, total_tokens FROM workflow_runs WHERE run_id = '6fa6ada1-dc7e-465b-85a8-8f005518f95b'"

# Monitor logs for TaskGroup errors
make logs | grep -i taskgroup
```

This bug report documents critical production issues requiring immediate attention to restore workflow system reliability.