# Autonomous QA Agent - Complete End-to-End Testing Mission

You are the autonomous QA Agent. Your mission is to **completely test the Claude Code workflow system while Felipe sleeps** and provide a comprehensive report on what works and what doesn't, enabling safe PR merging decisions.

## 🎯 Your Autonomous Mission

Execute **ALL 50 tests systematically**, monitor each one, document results, and generate a final report. Use `mcp__wait__*` tools liberally to work autonomously without human intervention.

## 🛠️ Your Available Tools

- `mcp__automagik_workflows__run_workflow()` - Execute workflows
- `mcp__automagik_workflows__get_workflow_status()` - Monitor progress  
- `mcp__automagik_workflows__list_recent_runs()` - Track all executions
- `mcp__wait__wait_minutes()` - Strategic autonomous waiting
- `Write()` - Document results as you go
- `Read()` - Check previous results
- `TodoWrite()` - Track your progress

## 🔄 Autonomous Execution Pattern

For each test:
1. **Execute** the workflow with specified parameters
2. **Wait strategically** (2-5 minutes) for initialization  
3. **Monitor progress** every 2 minutes until completion
4. **Document result** immediately
5. **Wait briefly** (30 seconds) before next test
6. **Update progress** in your todo list

## 📋 Complete Test Suite (50 Tests)

### Phase 1: Basic Functionality (21 tests)

**Test 1-7: Simple Execution**
```
1. BF-01: mcp__automagik_workflows__run_workflow(workflow_name="guardian", message="Perform a basic health check on the current codebase. Check for common issues like import errors, syntax problems, and basic security vulnerabilities.", session_name="qa_guardian_basic_health", max_turns=5)

2. BF-02: mcp__automagik_workflows__run_workflow(workflow_name="surgeon", message="Scan the codebase for any simple syntax errors, unused imports, or basic code quality issues. Fix what you find with minimal changes.", session_name="qa_surgeon_simple_fix", max_turns=5)

3. BF-03: mcp__automagik_workflows__run_workflow(workflow_name="brain", message="Analyze the current project structure and store key knowledge about Python best practices and architectural patterns.", session_name="qa_brain_knowledge_storage", max_turns=5)

4. BF-04: mcp__automagik_workflows__run_workflow(workflow_name="genie", message="Coordinate a simple documentation update task. Review existing documentation and improve one specific area.", session_name="qa_genie_simple_coordination", max_turns=5)

5. BF-05: mcp__automagik_workflows__run_workflow(workflow_name="shipper", message="Prepare a basic deployment checklist for this project. Review current configuration and identify deployment requirements.", session_name="qa_shipper_deployment_prep", max_turns=5)

6. BF-06: mcp__automagik_workflows__run_workflow(workflow_name="lina", message="Create a simple Linear issue for tracking QA test progress. Include relevant details about the testing initiative.", session_name="qa_lina_linear_integration", max_turns=5)

7. BF-07: mcp__automagik_workflows__run_workflow(workflow_name="builder", message="Create a simple 'hello world' utility function with proper documentation, type hints, and a basic test.", session_name="qa_builder_hello_world", max_turns=5)
```

**Test 8-14: Complex Tasks**
```
8. BF-08: mcp__automagik_workflows__run_workflow(workflow_name="guardian", message="Perform a comprehensive security audit of the authentication and API systems. Check for vulnerabilities and security best practices.", session_name="qa_guardian_security_audit", max_turns=15)

9. BF-09: mcp__automagik_workflows__run_workflow(workflow_name="surgeon", message="Identify and refactor any complex code modules that could benefit from improved maintainability while preserving functionality.", session_name="qa_surgeon_complex_refactor", max_turns=15)

10. BF-10: mcp__automagik_workflows__run_workflow(workflow_name="brain", message="Conduct a deep analysis of the project architecture. Store comprehensive knowledge about design patterns and component relationships.", session_name="qa_brain_architecture_analysis", max_turns=15)

11. BF-11: mcp__automagik_workflows__run_workflow(workflow_name="genie", message="Orchestrate a complete feature development lifecycle for a small utility. Coordinate planning, implementation, testing, and documentation.", session_name="qa_genie_full_lifecycle", max_turns=20)

12. BF-12: mcp__automagik_workflows__run_workflow(workflow_name="shipper", message="Set up comprehensive CI/CD pipeline configuration including testing, linting, security scanning, and deployment automation.", session_name="qa_shipper_cicd_setup", max_turns=15)

13. BF-13: mcp__automagik_workflows__run_workflow(workflow_name="lina", message="Synchronize current project status with Linear workspace. Update existing issues and ensure project tracking is current.", session_name="qa_lina_project_sync", max_turns=15)

14. BF-14: mcp__automagik_workflows__run_workflow(workflow_name="builder", message="Implement a comprehensive REST API endpoint with authentication, input validation, error handling, and documentation.", session_name="qa_builder_rest_api", max_turns=15)
```

**Test 15-18: Turn Limits**
```
15. BF-15: mcp__automagik_workflows__run_workflow(workflow_name="builder", message="Create a complex data processing pipeline with multiple stages. Work efficiently within the turn limit.", session_name="qa_builder_turn_limit", max_turns=3)

16. BF-16: mcp__automagik_workflows__run_workflow(workflow_name="guardian", message="Run an exhaustive test suite covering unit tests, integration tests, security tests, and performance validation.", session_name="qa_guardian_exhaustive", max_turns=10)

17. BF-17: mcp__automagik_workflows__run_workflow(workflow_name="surgeon", message="Identify and fix multiple interconnected code issues including performance problems and maintainability concerns.", session_name="qa_surgeon_multiple_issues", max_turns=5)

18. BF-18: mcp__automagik_workflows__run_workflow(workflow_name="genie", message="Coordinate a multi-step workflow optimization project with no turn restrictions. Take the time needed to do it properly.", session_name="qa_genie_unlimited", max_turns=null)
```

**Test 19-21: Timeouts**
```
19. BF-19: mcp__automagik_workflows__run_workflow(workflow_name="shipper", message="Test complete production deployment process including environment setup and deployment verification.", session_name="qa_shipper_production", timeout=3600)

20. BF-20: mcp__automagik_workflows__run_workflow(workflow_name="brain", message="Process and organize a large knowledge base including all project documentation and architectural decisions.", session_name="qa_brain_large_processing", timeout=7200)

21. BF-21: mcp__automagik_workflows__run_workflow(workflow_name="builder", message="Create a quick prototype implementation under time pressure. Focus on core functionality and rapid delivery.", session_name="qa_builder_quick_prototype", timeout=300)
```

### Phase 2: Repository & Git Tests (9 tests)

```
22. RS-01: mcp__automagik_workflows__run_workflow(workflow_name="builder", message="Work in the current repository to create a simple utility function. Test that local repository operations work correctly.", session_name="qa_local_repo_work", max_turns=5)

23. RS-02: mcp__automagik_workflows__run_workflow(workflow_name="guardian", message="Run tests specifically on the main branch. Validate branch-specific operations work correctly.", session_name="qa_specific_branch", git_branch="main", max_turns=8)

24. RS-03: mcp__automagik_workflows__run_workflow(workflow_name="surgeon", message="Fix any issues found on the main branch of the current repository. Test local git operations.", session_name="qa_local_branch_ops", git_branch="main", max_turns=6)

25. RS-04: mcp__automagik_workflows__run_workflow(workflow_name="builder", message="Simulate external repository work by creating a feature in an isolated workspace.", session_name="qa_external_repo_sim", max_turns=10)

26. RS-05: mcp__automagik_workflows__run_workflow(workflow_name="guardian", message="Simulate testing on external repository develop branch by testing in isolated environment.", session_name="qa_external_branch_sim", max_turns=8)

27. RS-06: mcp__automagik_workflows__run_workflow(workflow_name="surgeon", message="Simulate fixing issues in external repository by working in clean isolated workspace.", session_name="qa_external_fix_sim", max_turns=7)

28. RS-07: mcp__automagik_workflows__run_workflow(workflow_name="builder", message="Implement a new feature and automatically create a pull request when completed successfully.", session_name="qa_auto_pr_creation", create_pr_on_success=true, pr_title="feat: Add new feature from QA test", pr_body="This PR was automatically created by the QA testing system to validate PR creation functionality.", max_turns=8)

29. RS-08: mcp__automagik_workflows__run_workflow(workflow_name="surgeon", message="Fix a bug and create an automatic pull request for the fix.", session_name="qa_bugfix_pr", create_pr_on_success=true, pr_title="fix: Bug resolution from QA test", pr_body="Automated bug fix PR created during QA testing.", max_turns=6)

30. RS-09: mcp__automagik_workflows__run_workflow(workflow_name="shipper", message="Prepare deployment configuration without creating a pull request.", session_name="qa_no_pr_deployment", create_pr_on_success=false, max_turns=5)
```

### Phase 3: Persistence & Session Tests (9 tests)

```
31. PS-01: mcp__automagik_workflows__run_workflow(workflow_name="builder", message="Create a utility function in persistent workspace that should be retained after completion.", session_name="persistent-session-1", persistent=true, max_turns=6)

32. PS-02: mcp__automagik_workflows__run_workflow(workflow_name="guardian", message="Set up a persistent test environment with configuration files.", session_name="test-environment", persistent=true, max_turns=8)

33. PS-03: mcp__automagik_workflows__run_workflow(workflow_name="surgeon", message="Create surgical environment persistence with diagnostic files.", session_name="fix-workspace", persistent=true, max_turns=5)

34. PS-04: mcp__automagik_workflows__run_workflow(workflow_name="builder", message="Create a temporary function that should be cleaned up after completion.", session_name="temp-session-1", persistent=false, max_turns=5)

35. PS-05: mcp__automagik_workflows__run_workflow(workflow_name="guardian", message="Run tests in temporary environment that cleans up automatically.", session_name="temp-test", persistent=false, max_turns=6)

36. PS-06: mcp__automagik_workflows__run_workflow(workflow_name="surgeon", message="Auto-generated temporary workspace for quick fixes.", persistent=false, max_turns=4)

37. SM-01: mcp__automagik_workflows__run_workflow(workflow_name="builder", message="Create a new session with user tracking.", session_name="new-feature-dev", user_id="user-123", max_turns=6)

38. SM-02: mcp__automagik_workflows__run_workflow(workflow_name="guardian", message="Create anonymous session without user tracking.", session_name="qa-session", max_turns=5)

39. SM-03: mcp__automagik_workflows__run_workflow(workflow_name="surgeon", message="Test auto-generated session handling.", user_id="dev-456", max_turns=4)
```

### Phase 4: Error Handling Tests (6 tests)

```
40. EH-01: Try mcp__automagik_workflows__run_workflow(workflow_name="builder", message="") - Expected: validation error

41. EH-02: Try mcp__automagik_workflows__run_workflow(workflow_name="invalid-workflow", message="Test") - Expected: 404 error

42. EH-03: Try mcp__automagik_workflows__run_workflow(workflow_name="builder", message="Test", max_turns=250) - Expected: validation error

43. EH-04: Try mcp__automagik_workflows__run_workflow(workflow_name="builder", message="Test", timeout=20000) - Expected: validation error

44. EH-05: Try mcp__automagik_workflows__run_workflow(workflow_name="builder", message="Test", session_id="invalid-uuid") - Expected: validation error

45. EH-06: Try mcp__automagik_workflows__run_workflow(workflow_name="builder", message="Test", repository_url="not-a-url") - Expected: validation error
```

### Phase 5: Performance Tests (2 tests)

```
46. PF-01: Execute 5 guardian workflows sequentially, measure performance

47. PF-02: Execute 3 workflows concurrently (guardian, builder, surgeon), check for conflicts
```

### Phase 6: Integration Tests (3 tests)

```
48. IT-01: Execute sequence: lina → builder → guardian → shipper

49. IT-02: Execute sequence: brain → surgeon → guardian  

50. IT-03: Execute sequence: builder → brain → guardian
```

## 🤖 Autonomous Execution Script

```python
# Your autonomous execution pattern:

import time
from datetime import datetime

# Initialize tracking
test_results = []
current_test = 1
total_tests = 50

# Update your todo list at start
TodoWrite(todos=[
    {"content": f"Execute all {total_tests} QA tests autonomously", "status": "in_progress", "priority": "high", "id": "1"},
    {"content": "Monitor each test until completion", "status": "pending", "priority": "high", "id": "2"},
    {"content": "Document results systematically", "status": "pending", "priority": "high", "id": "3"},
    {"content": "Generate final QA report", "status": "pending", "priority": "high", "id": "4"}
])

# For each test in your list above:
for test in all_tests:
    print(f"🧪 Starting Test {current_test}/{total_tests}: {test['id']}")
    
    # 1. Execute workflow
    start_time = datetime.now()
    result = mcp__automagik_workflows__run_workflow(**test['params'])
    run_id = result['run_id']
    
    # 2. Wait for initialization
    mcp__wait__wait_minutes(duration=2)
    
    # 3. Monitor until completion
    status = "running"
    while status in ["pending", "running"]:
        status_result = mcp__automagik_workflows__get_workflow_status(run_id, detailed=true)
        status = status_result['status']
        
        if status in ["pending", "running"]:
            mcp__wait__wait_minutes(duration=2)  # Check every 2 minutes
        
        # Safety timeout after 30 minutes
        if (datetime.now() - start_time).total_seconds() > 1800:
            status = "timeout"
            break
    
    # 4. Document result immediately
    test_result = {
        "test_id": test['id'],
        "workflow": test['workflow'],
        "status": status,
        "execution_time": (datetime.now() - start_time).total_seconds(),
        "turns_used": status_result.get('progress', {}).get('turns', 0),
        "cost_usd": status_result.get('metrics', {}).get('cost_usd', 0),
        "tokens": status_result.get('metrics', {}).get('tokens', {}).get('total', 0),
        "tools_used": status_result.get('metrics', {}).get('tools_used', []),
        "files_created": status_result.get('result', {}).get('files_created', []),
        "error_message": status_result.get('result', {}).get('message') if status != "completed" else None
    }
    
    test_results.append(test_result)
    
    # Write results incrementally
    Write(file_path=f"/home/namastex/workspace/am-agents-labs/qa_test_{test['id']}_result.json", 
          content=json.dumps(test_result, indent=2))
    
    # Update progress
    print(f"✅ Test {current_test}/{total_tests} completed: {status}")
    current_test += 1
    
    # Brief pause before next test
    mcp__wait__wait_minutes(duration=0.5)

# Update todo when done
TodoWrite(todos=[
    {"content": f"Execute all {total_tests} QA tests autonomously", "status": "completed", "priority": "high", "id": "1"},
    {"content": "Monitor each test until completion", "status": "completed", "priority": "high", "id": "2"},
    {"content": "Document results systematically", "status": "completed", "priority": "high", "id": "3"},
    {"content": "Generate final QA report", "status": "in_progress", "priority": "high", "id": "4"}
])
```

## 📊 Final Report Generation

After completing ALL 50 tests, generate this comprehensive report:

```python
# Calculate summary statistics
total_tests = len(test_results)
passed_tests = len([r for r in test_results if r['status'] == 'completed'])
failed_tests = len([r for r in test_results if r['status'] in ['failed', 'error']])
timeout_tests = len([r for r in test_results if r['status'] == 'timeout'])
success_rate = (passed_tests / total_tests) * 100

# Workflow breakdown
workflows = ['guardian', 'builder', 'surgeon', 'genie', 'shipper', 'lina', 'brain']
workflow_stats = {}
for workflow in workflows:
    workflow_tests = [r for r in test_results if workflow in r.get('workflow', '')]
    workflow_stats[workflow] = {
        'total': len(workflow_tests),
        'passed': len([r for r in workflow_tests if r['status'] == 'completed']),
        'success_rate': len([r for r in workflow_tests if r['status'] == 'completed']) / len(workflow_tests) * 100 if workflow_tests else 0
    }

# Feature category breakdown
categories = {
    'basic_functionality': [r for r in test_results if r['test_id'].startswith('BF-')],
    'repository_operations': [r for r in test_results if r['test_id'].startswith('RS-')],
    'persistence': [r for r in test_results if r['test_id'].startswith('PS-')],
    'session_management': [r for r in test_results if r['test_id'].startswith('SM-')],
    'error_handling': [r for r in test_results if r['test_id'].startswith('EH-')],
    'performance': [r for r in test_results if r['test_id'].startswith('PF-')],
    'integration': [r for r in test_results if r['test_id'].startswith('IT-')]
}

category_stats = {}
for category, tests in categories.items():
    if tests:
        category_stats[category] = {
            'total': len(tests),
            'passed': len([r for r in tests if r['status'] == 'completed']),
            'success_rate': len([r for r in tests if r['status'] == 'completed']) / len(tests) * 100
        }

# Generate the final report
final_report = f"""
# 🧪 Autonomous QA Testing Report - Claude Code Workflow System
## Executed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 📊 Executive Summary
- **Total Tests Executed**: {total_tests}
- **Passed**: {passed_tests} ✅
- **Failed**: {failed_tests} ❌
- **Timeouts**: {timeout_tests} ⏰
- **Overall Success Rate**: {success_rate:.1f}%

## 🚨 Critical Issues Found
{generate_critical_issues_section(test_results)}

## ✅ What Works Well
{generate_working_well_section(test_results)}

## ⚠️ What Needs Attention
{generate_needs_attention_section(test_results)}

## 🔧 Workflow-Specific Results
{generate_workflow_breakdown(workflow_stats)}

## 📈 Feature Category Results
{generate_category_breakdown(category_stats)}

## 🔒 PR Merging Recommendations

### ✅ SAFE TO MERGE if:
- Basic Functionality: {category_stats.get('basic_functionality', {}).get('success_rate', 0):.1f}% (Target: 85%+)
- Repository Operations: {category_stats.get('repository_operations', {}).get('success_rate', 0):.1f}% (Target: 80%+)
- Error Handling: {category_stats.get('error_handling', {}).get('success_rate', 0):.1f}% (Target: 100%)
- No critical workflow failures
- All 7 workflows have basic functionality

### Current Status: {determine_merge_safety(category_stats, workflow_stats)}

## 📋 Detailed Test Results
{generate_detailed_results(test_results)}

## 🏁 Testing Completed Autonomously
This comprehensive QA report was generated autonomously while Felipe slept.
All {total_tests} tests were executed systematically with autonomous monitoring.
"""

# Write the final report
Write(file_path="/home/namastex/workspace/am-agents-labs/AUTONOMOUS_QA_REPORT.md", content=final_report)

# Update final todo
TodoWrite(todos=[
    {"content": f"Execute all {total_tests} QA tests autonomously", "status": "completed", "priority": "high", "id": "1"},
    {"content": "Monitor each test until completion", "status": "completed", "priority": "high", "id": "2"},
    {"content": "Document results systematically", "status": "completed", "priority": "high", "id": "3"},
    {"content": "Generate final QA report", "status": "completed", "priority": "high", "id": "4"}
])

print("🎉 AUTONOMOUS QA TESTING COMPLETE!")
print(f"📊 Final Results: {passed_tests}/{total_tests} tests passed ({success_rate:.1f}%)")
print("📝 Report saved to: AUTONOMOUS_QA_REPORT.md")
print("💤 Felipe can wake up to a fully tested system!")
```


## 🚀 Start Your Autonomous Mission

Execute this systematically, use wait tools liberally, monitor everything, document comprehensively, and provide Felipe with a complete report when he wakes up!

**Your mission: Test everything, break nothing, report accurately, enable safe PR merging!**
make sure to clean up after yourself (like worktrees, etc in the end)