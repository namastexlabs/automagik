# 🧪 **WORKFLOW QA TESTING PROCEDURE**

## **Procedure Overview**
Comprehensive testing of workflow execution, database persistence, and MCP workflow tools for both persistent and non-persistent modes.

## **Prerequisites**
- Server running on port 28881
- Fresh database with applied migrations
- Clean workspaces
- All MCP servers connected

## **Test Procedure Steps**

### **Phase 1: Database Verification**
1. **Verify workflow_runs table exists and schema**
   ```bash
   mcp__mcp-sqlite__list_tables
   mcp__mcp-sqlite__get_table_schema workflow_runs
   ```

2. **Check initial table state**
   ```bash
   mcp__mcp-sqlite__read_records workflow_runs
   ```

### **Phase 2: MCP Workflow Tools Testing**

#### **2.1 List Available Workflows**
```bash
mcp__automagik-workflows__list_workflows
```
**Expected**: List of all available workflows (genie, guardian, builder, surgeon, etc.)

#### **2.2 Test Workflow Execution**
```bash
mcp__automagik-workflows__run_workflow
- workflow_name: "guardian" 
- message: "QA Test - Simple file analysis task"
- max_turns: 10
- session_name: "qa-test-1"
```
**Expected**: Return run_id and pending status

#### **2.3 Test Status Monitoring**
```bash
mcp__automagik-workflows__get_workflow_status [run_id]
mcp__automagik-workflows__get_workflow_status [run_id] detailed=true
```
**Expected**: Real-time status updates with progress tracking

#### **2.4 Test Recent Runs Listing**
```bash
mcp__automagik-workflows__list_recent_runs page_size=10
```
**Expected**: List of recent workflow executions with metadata

#### **2.5 Test Kill Functionality**
```bash
mcp__automagik-workflows__kill_workflow [run_id]
```
**Expected**: Graceful workflow termination

### **Phase 3: Database Persistence Verification**

#### **3.1 Check Workflow Record Creation**
```bash
mcp__mcp-sqlite__read_records workflow_runs
```
**Expected**: New record with run_id, workflow_name, status, timestamps

#### **3.2 Verify Rich Data Storage**
```bash
mcp__mcp-sqlite__query "SELECT run_id, workflow_name, status, metadata, created_at FROM workflow_runs ORDER BY created_at DESC LIMIT 5"
```
**Expected**: Detailed workflow metadata for UI dashboard

### **Phase 4: Concurrent Execution Testing**

#### **4.1 Launch Multiple Workflows**
- Start 3 different workflows simultaneously
- Monitor with `make logs` for TaskGroup conflicts
- Check database records for all executions

#### **4.2 Live Orchestration Testing**
- Start long-running workflow
- Monitor status in real-time
- Test kill during execution
- Verify cleanup in database

### **Phase 5: API Endpoints Testing**

#### **5.1 REST API Validation**
```bash
curl -X GET http://localhost:28881/api/v1/workflows/claude-code/runs
curl -X GET http://localhost:28881/api/v1/workflows/claude-code/runs/[run_id]
```
**Expected**: Rich JSON data for UI dashboard integration

### **Phase 6: Error Scenarios Testing**

#### **6.1 Invalid Workflow Name**
```bash
mcp__automagik-workflows__run_workflow workflow_name="nonexistent"
```
**Expected**: Clear error message

#### **6.2 Invalid Run ID**
```bash
mcp__automagik-workflows__get_workflow_status "invalid-uuid"
```
**Expected**: Appropriate error handling

#### **6.3 Database Corruption Simulation**
- Test behavior with missing records
- Test with corrupted workflow data

## **Success Criteria**

### **✅ PASS Requirements**
- [ ] workflow_runs table exists with correct schema
- [ ] All MCP workflow tools respond correctly
- [ ] Workflows execute and persist to database
- [ ] Real-time status monitoring works
- [ ] Kill functionality works gracefully
- [ ] API endpoints return rich data
- [ ] No TaskGroup conflicts in logs
- [ ] Concurrent executions work properly

### **❌ FAIL Indicators**
- Missing or incorrect database schema
- MCP tools returning errors
- Workflows not persisting to database
- Status monitoring not updating
- Kill functionality not working
- API endpoints returning 500 errors
- TaskGroup conflicts in logs
- Database corruption or inconsistency

## **Bug Classification**

### **🔴 Critical Bugs**
- Database schema issues
- Complete workflow execution failure
- Data corruption or loss

### **🟡 Major Bugs**
- Status monitoring not working
- Kill functionality broken
- API endpoints failing

### **🟢 Minor Bugs**
- UI data formatting issues
- Non-critical error messages
- Performance optimization opportunities

## **Execution Notes**
- Run `make logs` continuously during testing
- Document all error messages exactly
- Record timestamps for debugging
- Save all run_ids for verification
- Take screenshots of any UI issues

## **Post-Test Actions**
- Clean up test workflows
- Reset database if needed
- Document all findings
- Create bug reports for failures
- Update procedure based on results