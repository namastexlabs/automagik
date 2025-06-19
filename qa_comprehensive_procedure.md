# 🔬 **COMPREHENSIVE WORKFLOW QA PROCEDURE**

## **Real-World Testing Protocol**

This QA procedure tests actual workflow functionality with complex multi-turn tasks, workspace management, git operations, and comprehensive validation.

## **Pre-Test Setup**
1. **Server Status Check**
   ```bash
   make status
   make logs  # Monitor throughout testing
   ```

2. **Database State Verification**
   ```python
   mcp__mcp-sqlite__query("SELECT COUNT(*) as total_runs FROM workflow_runs")
   mcp__mcp-sqlite__query("SELECT run_id, workflow_name, status FROM workflow_runs ORDER BY created_at DESC LIMIT 5")
   ```

3. **Git State Check**
   ```python
   mcp__git__git_status(repo_path="/home/namastex/workspace/am-agents-labs")
   mcp__git__git_log(repo_path="/home/namastex/workspace/am-agents-labs", max_count=3)
   ```

## **TEST SCENARIOS**

### **Scenario A: Complex UI Implementation Task**
**Objective**: Test multi-turn complex implementation with persistent workspace

**Task**: "Enhance the workflow dashboard UI to show real-time progress updates with websockets, add filtering by workflow type, and implement a workflow kill button with confirmation dialog"

**Test Steps**:
1. **Launch Complex Builder Task**
   ```python
   builder_run = mcp__automagik-workflows__run_workflow(
       workflow_name="builder",
       message="Enhance the workflow dashboard UI in automagik-ui/ to show real-time progress updates with websockets, add filtering by workflow type, and implement a workflow kill button with confirmation dialog. Use proper TypeScript types and follow existing UI patterns.",
       max_turns=30,
       session_name="qa-ui-enhancement",
       persistent=True
   )
   ```

2. **Monitor Multi-Turn Execution**
   ```bash
   # Watch logs continuously
   make logs -f
   
   # Check status every 60 seconds
   mcp__wait__wait_minutes(1)
   status_1 = mcp__automagik-workflows__get_workflow_status(builder_run["run_id"], detailed=True)
   
   mcp__wait__wait_minutes(2)
   status_2 = mcp__automagik-workflows__get_workflow_status(builder_run["run_id"], detailed=True)
   
   mcp__wait__wait_minutes(3)
   status_3 = mcp__automagik-workflows__get_workflow_status(builder_run["run_id"], detailed=True)
   ```

3. **Validate Workspace Management**
   ```python
   # Check workspace creation
   mcp__mcp-sqlite__query("SELECT workspace_path, workspace_persistent FROM workflow_runs WHERE run_id = ?", [builder_run["run_id"]])
   
   # Verify files in worktree
   workspace_path = status_3["debug"]["session_info"]["workspace_path"]  # From status
   
   # List files created
   bash("find {workspace_path} -name '*.tsx' -o -name '*.ts' -o -name '*.json' | head -20")
   
   # Check git status in workspace
   mcp__git__git_status(repo_path=workspace_path)
   ```

4. **Validate Implementation Quality**
   ```python
   # Check if TypeScript files were created
   bash("find {workspace_path}/automagik-ui -name '*.tsx' -exec head -5 {} \\;")
   
   # Verify imports and types
   bash("grep -r 'WebSocket\\|useState\\|useEffect' {workspace_path}/automagik-ui/")
   
   # Check for proper component structure
   bash("grep -r 'interface\\|type' {workspace_path}/automagik-ui/")
   ```

5. **Git Integration Validation**
   ```python
   # Check if commits were made
   mcp__git__git_log(repo_path=workspace_path, max_count=5)
   
   # Verify commit messages include Claude co-authoring
   bash("git log --oneline -5 | grep -i claude")
   
   # Check branch creation
   bash("git branch -a | grep -E 'feature|ui|enhancement'")
   ```

6. **Database Persistence Validation**
   ```python
   # Verify rich metadata capture
   mcp__mcp-sqlite__query("""
       SELECT 
           workflow_name, status, git_branch, 
           git_diff_files_changed, git_diff_added_lines,
           cost_estimate, total_tokens, duration_seconds
       FROM workflow_runs 
       WHERE run_id = ?
   """, [builder_run["run_id"]])
   
   # Check metadata JSON
   mcp__mcp-sqlite__query("SELECT metadata FROM workflow_runs WHERE run_id = ?", [builder_run["run_id"]])
   ```

### **Scenario B: Concurrent Multi-Workflow Testing**
**Objective**: Test multiple workflows running simultaneously with different workspace modes

**Test Steps**:
1. **Launch Multiple Workflows**
   ```python
   # Persistent workspace
   guardian_run = mcp__automagik-workflows__run_workflow(
       workflow_name="guardian",
       message="Perform comprehensive security audit of the UI components, check for XSS vulnerabilities and proper input validation",
       max_turns=20,
       session_name="qa-security-audit",
       persistent=True
   )
   
   # Temporary workspace  
   surgeon_run = mcp__automagik-workflows__run_workflow(
       workflow_name="surgeon",
       message="Debug and fix any TypeScript compilation errors in the UI enhancement",
       max_turns=15,
       session_name="qa-typescript-fixes",
       persistent=False
   )
   
   # Another builder task
   builder2_run = mcp__automagik-workflows__run_workflow(
       workflow_name="builder",
       message="Add comprehensive tests for the new UI components using Jest and React Testing Library",
       max_turns=25,
       session_name="qa-testing-implementation",
       persistent=True
   )
   ```

2. **Monitor Concurrent Execution**
   ```bash
   # Check all running workflows
   mcp__automagik-workflows__list_recent_runs(page_size=10)
   
   # Monitor logs for conflicts
   make logs | grep -E "ERROR|WARN|TaskGroup|conflict"
   
   # Check database load
   mcp__mcp-sqlite__query("SELECT COUNT(*) as active_workflows FROM workflow_runs WHERE status = 'running'")
   ```

3. **Validate Workspace Isolation**
   ```python
   # Get workspace paths for each
   guardian_status = mcp__automagik-workflows__get_workflow_status(guardian_run["run_id"])
   surgeon_status = mcp__automagik-workflows__get_workflow_status(surgeon_run["run_id"])
   builder2_status = mcp__automagik-workflows__get_workflow_status(builder2_run["run_id"])
   
   # Verify different workspace paths
   bash("ls -la /tmp/ | grep claude-workspace")  # Check temp workspaces
   bash("ls -la ./worktrees/ | grep builder")    # Check persistent workspaces
   ```

### **Scenario C: Workflow Kill and Recovery Testing**
**Objective**: Test workflow termination and cleanup

**Test Steps**:
1. **Start Long-Running Workflow**
   ```python
   long_run = mcp__automagik-workflows__run_workflow(
       workflow_name="builder",
       message="Implement a complete microservices architecture with Docker, Kubernetes, monitoring, and CI/CD pipeline",
       max_turns=50,
       session_name="qa-long-task"
   )
   ```

2. **Monitor and Kill**
   ```python
   mcp__wait__wait_minutes(2)  # Let it start working
   
   # Check it's actually running
   status = mcp__automagik-workflows__get_workflow_status(long_run["run_id"])
   
   # Kill the workflow
   kill_result = mcp__automagik-workflows__kill_workflow(long_run["run_id"])
   ```

3. **Validate Cleanup**
   ```python
   # Check final status
   final_status = mcp__automagik-workflows__get_workflow_status(long_run["run_id"])
   
   # Verify database state
   mcp__mcp-sqlite__query("SELECT status, completed_at FROM workflow_runs WHERE run_id = ?", [long_run["run_id"]])
   
   # Check workspace cleanup
   bash("ps aux | grep claude")  # Should not show the killed process
   ```

## **VALIDATION CRITERIA**

### **✅ PASS Requirements**
- [ ] All workflows start successfully with proper run_ids
- [ ] Multi-turn execution works (progress through multiple turns)
- [ ] Database captures rich metadata (git info, costs, tokens)
- [ ] Workspace management works (persistent vs temporary)
- [ ] Files are created in correct worktree locations
- [ ] Git operations work (commits, branches, co-authoring)
- [ ] Concurrent workflows don't interfere
- [ ] Kill functionality works with proper cleanup
- [ ] No TaskGroup conflicts in logs
- [ ] API endpoints return accurate data

### **🔧 Detailed Validation Checks**

#### **File Creation Validation**
```bash
# Check TypeScript files
find {workspace_path} -name "*.tsx" -exec echo "=== {} ===" \\; -exec head -10 {} \\;

# Check proper imports
grep -r "import.*from" {workspace_path}/automagik-ui/

# Verify component structure
grep -r "export.*function\|export.*const" {workspace_path}/automagik-ui/
```

#### **Git Integration Validation**
```bash
# Check commit history
git log --oneline -10 | grep "Claude"

# Verify branch naming
git branch -a | grep -E "feature|fix|enhancement"

# Check co-authoring
git log --pretty=fuller -5 | grep -A 5 "Co-authored-by"
```

#### **Database Validation**
```python
# Verify comprehensive data capture
mcp__mcp-sqlite__query("""
    SELECT 
        COUNT(*) as total_fields_populated
    FROM workflow_runs 
    WHERE run_id = ? 
        AND workspace_path IS NOT NULL
        AND git_branch IS NOT NULL
        AND total_tokens > 0
""", [run_id])
```

#### **Performance Validation**
```bash
# Check memory usage
ps aux | grep python | awk '{print $4}' | paste -sd+ | bc

# Check disk usage of workspaces
du -sh ./worktrees/*/

# Monitor CPU during execution
top -p $(pgrep -f "python.*claude") -n 1
```

## **BUG CLASSIFICATION**

### **🔴 Critical Bugs**
- Workflow fails to start
- Database corruption
- Workspace conflicts
- Git operations fail
- TaskGroup conflicts

### **🟡 Major Bugs**  
- Multi-turn execution stops early
- Incomplete file creation
- Missing git commits
- Incorrect metadata

### **🟢 Minor Bugs**
- Formatting issues
- Non-critical warnings
- Performance degradation

## **DOCUMENTATION REQUIREMENTS**

For each test scenario, document:
1. **Exact commands run**
2. **Expected vs actual output**
3. **Workspace paths and files created**
4. **Git commits and branches**
5. **Database records**
6. **Log excerpts (errors/warnings)**
7. **Performance metrics**
8. **Screenshots of any UI changes**

## **EXECUTION PROTOCOL**

1. **Start with clean state** (fresh database, no running workflows)
2. **Run ONE scenario at a time** initially
3. **Monitor logs continuously** during execution
4. **Document EVERYTHING** as you go
5. **Validate ALL criteria** before marking pass/fail
6. **Test edge cases** and failure scenarios
7. **Measure performance impact**

This comprehensive approach ensures we test the complete workflow lifecycle with real-world complexity!