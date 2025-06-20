# QA Agent Master Task Prompt

## Mission
You are the QA Agent responsible for comprehensive testing of the Claude Code workflow system. Execute all tests systematically, document results, and provide a clear report on what works and what doesn't in the current codebase state.

## Your Task List

Execute these tests **one by one** in order. For each test, document the results and move to the next.

### Phase 1: Basic Functionality Tests (21 tests)

#### Simple Execution Tests (7 tests)
1. **BF-01**: Test `guardian` basic health check
   ```
   mcp__automagik_workflows__run_workflow(
     workflow_name="guardian",
     message="Perform a basic health check on the current codebase. Check for common issues like import errors, syntax problems, and basic security vulnerabilities.",
     session_name="qa_guardian_basic_health",
     max_turns=5
   )
   ```

2. **BF-02**: Test `surgeon` simple fixes
   ```
   mcp__automagik_workflows__run_workflow(
     workflow_name="surgeon",
     message="Scan the codebase for any simple syntax errors, unused imports, or basic code quality issues. Fix what you find with minimal changes.",
     session_name="qa_surgeon_simple_fix",
     max_turns=5
   )
   ```

3. **BF-03**: Test `brain` knowledge storage
   ```
   mcp__automagik_workflows__run_workflow(
     workflow_name="brain",
     message="Analyze the current project structure and store key knowledge about Python best practices and architectural patterns.",
     session_name="qa_brain_knowledge_storage",
     max_turns=5
   )
   ```

4. **BF-04**: Test `genie` coordination
   ```
   mcp__automagik_workflows__run_workflow(
     workflow_name="genie",
     message="Coordinate a simple documentation update task. Review existing documentation and improve one specific area.",
     session_name="qa_genie_simple_coordination",
     max_turns=5
   )
   ```

5. **BF-05**: Test `shipper` deployment prep
   ```
   mcp__automagik_workflows__run_workflow(
     workflow_name="shipper",
     message="Prepare a basic deployment checklist for this project. Review current configuration and identify deployment requirements.",
     session_name="qa_shipper_deployment_prep",
     max_turns=5
   )
   ```

6. **BF-06**: Test `lina` Linear integration
   ```
   mcp__automagik_workflows__run_workflow(
     workflow_name="lina",
     message="Create a simple Linear issue for tracking QA test progress. Include relevant details about the testing initiative.",
     session_name="qa_lina_linear_integration",
     max_turns=5
   )
   ```

7. **BF-07**: Test `builder` simple implementation
   ```
   mcp__automagik_workflows__run_workflow(
     workflow_name="builder",
     message="Create a simple 'hello world' utility function with proper documentation, type hints, and a basic test.",
     session_name="qa_builder_hello_world",
     max_turns=5
   )
   ```

#### Complex Task Tests (7 tests)
8. **BF-08**: Test `guardian` security audit
   ```
   mcp__automagik_workflows__run_workflow(
     workflow_name="guardian",
     message="Perform a comprehensive security audit of the authentication and API systems. Check for vulnerabilities and security best practices.",
     session_name="qa_guardian_security_audit",
     max_turns=15
   )
   ```

9. **BF-09**: Test `surgeon` complex refactoring
   ```
   mcp__automagik_workflows__run_workflow(
     workflow_name="surgeon",
     message="Identify and refactor any complex code modules that could benefit from improved maintainability while preserving functionality.",
     session_name="qa_surgeon_complex_refactor",
     max_turns=15
   )
   ```

10. **BF-10**: Test `brain` architecture analysis
    ```
    mcp__automagik_workflows__run_workflow(
      workflow_name="brain",
      message="Conduct a deep analysis of the project architecture. Store comprehensive knowledge about design patterns and component relationships.",
      session_name="qa_brain_architecture_analysis",
      max_turns=15
    )
    ```

11. **BF-11**: Test `genie` full lifecycle orchestration
    ```
    mcp__automagik_workflows__run_workflow(
      workflow_name="genie",
      message="Orchestrate a complete feature development lifecycle for a small utility. Coordinate planning, implementation, testing, and documentation.",
      session_name="qa_genie_full_lifecycle",
      max_turns=20
    )
    ```

12. **BF-12**: Test `shipper` CI/CD setup
    ```
    mcp__automagik_workflows__run_workflow(
      workflow_name="shipper",
      message="Set up comprehensive CI/CD pipeline configuration including testing, linting, security scanning, and deployment automation.",
      session_name="qa_shipper_cicd_setup",
      max_turns=15
    )
    ```

13. **BF-13**: Test `lina` project synchronization
    ```
    mcp__automagik_workflows__run_workflow(
      workflow_name="lina",
      message="Synchronize current project status with Linear workspace. Update existing issues and ensure project tracking is current.",
      session_name="qa_lina_project_sync",
      max_turns=15
    )
    ```

14. **BF-14**: Test `builder` REST API implementation
    ```
    mcp__automagik_workflows__run_workflow(
      workflow_name="builder",
      message="Implement a comprehensive REST API endpoint with authentication, input validation, error handling, and documentation.",
      session_name="qa_builder_rest_api",
      max_turns=15
    )
    ```

#### Turn Limit Tests (4 tests)
15. **BF-15**: Test `builder` with turn constraint
    ```
    mcp__automagik_workflows__run_workflow(
      workflow_name="builder",
      message="Create a complex data processing pipeline with multiple stages. Work efficiently within the turn limit.",
      session_name="qa_builder_turn_limit",
      max_turns=3
    )
    ```

16. **BF-16**: Test `guardian` exhaustive testing
    ```
    mcp__automagik_workflows__run_workflow(
      workflow_name="guardian",
      message="Run an exhaustive test suite covering unit tests, integration tests, security tests, and performance validation.",
      session_name="qa_guardian_exhaustive",
      max_turns=10
    )
    ```

17. **BF-17**: Test `surgeon` multiple issues
    ```
    mcp__automagik_workflows__run_workflow(
      workflow_name="surgeon",
      message="Identify and fix multiple interconnected code issues including performance problems and maintainability concerns.",
      session_name="qa_surgeon_multiple_issues",
      max_turns=5
    )
    ```

18. **BF-18**: Test `genie` unlimited coordination
    ```
    mcp__automagik_workflows__run_workflow(
      workflow_name="genie",
      message="Coordinate a multi-step workflow optimization project with no turn restrictions. Take the time needed to do it properly.",
      session_name="qa_genie_unlimited",
      max_turns=null
    )
    ```

#### Timeout Tests (3 tests)
19. **BF-19**: Test `shipper` production deployment
    ```
    mcp__automagik_workflows__run_workflow(
      workflow_name="shipper",
      message="Test complete production deployment process including environment setup and deployment verification.",
      session_name="qa_shipper_production",
      timeout=3600
    )
    ```

20. **BF-20**: Test `brain` large knowledge processing
    ```
    mcp__automagik_workflows__run_workflow(
      workflow_name="brain",
      message="Process and organize a large knowledge base including all project documentation and architectural decisions.",
      session_name="qa_brain_large_processing",
      timeout=7200
    )
    ```

21. **BF-21**: Test `builder` quick prototype
    ```
    mcp__automagik_workflows__run_workflow(
      workflow_name="builder",
      message="Create a quick prototype implementation under time pressure. Focus on core functionality and rapid delivery.",
      session_name="qa_builder_quick_prototype",
      timeout=300
    )
    ```

### Phase 2: Repository & Git Integration Tests (9 tests)

22. **RS-01**: Local repository work
    ```
    mcp__automagik_workflows__run_workflow(
      workflow_name="builder",
      message="Work in the current repository to create a simple utility function. Test that local repository operations work correctly.",
      session_name="qa_local_repo_work",
      max_turns=5
    )
    ```

23. **RS-02**: Specific branch work
    ```
    mcp__automagik_workflows__run_workflow(
      workflow_name="guardian",
      message="Run tests specifically on the main branch. Validate branch-specific operations work correctly.",
      session_name="qa_specific_branch",
      git_branch="main",
      max_turns=8
    )
    ```

24. **RS-03**: Local branch operations
    ```
    mcp__automagik_workflows__run_workflow(
      workflow_name="surgeon",
      message="Fix any issues found on the main branch of the current repository. Test local git operations.",
      session_name="qa_local_branch_ops",
      git_branch="main",
      max_turns=6
    )
    ```

25. **RS-04**: External repository (simulated)
    ```
    mcp__automagik_workflows__run_workflow(
      workflow_name="builder",
      message="Simulate external repository work by creating a feature in an isolated workspace.",
      session_name="qa_external_repo_sim",
      max_turns=10
    )
    ```

26. **RS-05**: External branch testing (simulated)
    ```
    mcp__automagik_workflows__run_workflow(
      workflow_name="guardian",
      message="Simulate testing on external repository develop branch by testing in isolated environment.",
      session_name="qa_external_branch_sim",
      max_turns=8
    )
    ```

27. **RS-06**: External repository fixes (simulated)
    ```
    mcp__automagik_workflows__run_workflow(
      workflow_name="surgeon",
      message="Simulate fixing issues in external repository by working in clean isolated workspace.",
      session_name="qa_external_fix_sim",
      max_turns=7
    )
    ```

28. **RS-07**: Automatic PR creation
    ```
    mcp__automagik_workflows__run_workflow(
      workflow_name="builder",
      message="Implement a new feature and automatically create a pull request when completed successfully.",
      session_name="qa_auto_pr_creation",
      create_pr_on_success=true,
      pr_title="feat: Add new feature from QA test",
      pr_body="This PR was automatically created by the QA testing system to validate PR creation functionality.",
      max_turns=8
    )
    ```

29. **RS-08**: Bug fix PR creation
    ```
    mcp__automagik_workflows__run_workflow(
      workflow_name="surgeon",
      message="Fix a bug and create an automatic pull request for the fix.",
      session_name="qa_bugfix_pr",
      create_pr_on_success=true,
      pr_title="fix: Bug resolution from QA test",
      pr_body="Automated bug fix PR created during QA testing.",
      max_turns=6
    )
    ```

30. **RS-09**: No PR deployment
    ```
    mcp__automagik_workflows__run_workflow(
      workflow_name="shipper",
      message="Prepare deployment configuration without creating a pull request.",
      session_name="qa_no_pr_deployment",
      create_pr_on_success=false,
      max_turns=5
    )
    ```

### Phase 3: Persistence & Session Tests (18 tests)

31. **PS-01**: Persistent workspace creation
    ```
    mcp__automagik_workflows__run_workflow(
      workflow_name="builder",
      message="Create a utility function in persistent workspace that should be retained after completion.",
      session_name="persistent-session-1",
      persistent=true,
      max_turns=6
    )
    ```

32. **PS-02**: Persistent test environment
    ```
    mcp__automagik_workflows__run_workflow(
      workflow_name="guardian",
      message="Set up a persistent test environment with configuration files.",
      session_name="test-environment",
      persistent=true,
      max_turns=8
    )
    ```

33. **PS-03**: Persistent surgical environment
    ```
    mcp__automagik_workflows__run_workflow(
      workflow_name="surgeon",
      message="Create surgical environment persistence with diagnostic files.",
      session_name="fix-workspace",
      persistent=true,
      max_turns=5
    )
    ```

34. **PS-04**: Temporary workspace cleanup
    ```
    mcp__automagik_workflows__run_workflow(
      workflow_name="builder",
      message="Create a temporary function that should be cleaned up after completion.",
      session_name="temp-session-1",
      persistent=false,
      max_turns=5
    )
    ```

35. **PS-05**: Temporary test environment
    ```
    mcp__automagik_workflows__run_workflow(
      workflow_name="guardian",
      message="Run tests in temporary environment that cleans up automatically.",
      session_name="temp-test",
      persistent=false,
      max_turns=6
    )
    ```

36. **PS-06**: Auto-generated temporary workspace
    ```
    mcp__automagik_workflows__run_workflow(
      workflow_name="surgeon",
      message="Auto-generated temporary workspace for quick fixes.",
      persistent=false,
      max_turns=4
    )
    ```

37. **SM-01**: New session with user tracking
    ```
    mcp__automagik_workflows__run_workflow(
      workflow_name="builder",
      message="Create a new session with user tracking.",
      session_name="new-feature-dev",
      user_id="user-123",
      max_turns=6
    )
    ```

38. **SM-02**: Anonymous session creation
    ```
    mcp__automagik_workflows__run_workflow(
      workflow_name="guardian",
      message="Create anonymous session without user tracking.",
      session_name="qa-session",
      max_turns=5
    )
    ```

39. **SM-03**: Auto-generated session
    ```
    mcp__automagik_workflows__run_workflow(
      workflow_name="surgeon",
      message="Test auto-generated session handling.",
      user_id="dev-456",
      max_turns=4
    )
    ```

### Phase 4: Error Handling Tests (6 tests)

40. **EH-01**: Test empty message validation
    - Try: `mcp__automagik_workflows__run_workflow(workflow_name="builder", message="")`
    - Expected: Should return validation error about required message

41. **EH-02**: Test invalid workflow name
    - Try: `mcp__automagik_workflows__run_workflow(workflow_name="invalid-workflow", message="Test")`
    - Expected: Should return 404 error with available workflows listed

42. **EH-03**: Test excessive turn limit
    - Try: `mcp__automagik_workflows__run_workflow(workflow_name="builder", message="Test", max_turns=250)`
    - Expected: Should return validation error about turn limit

43. **EH-04**: Test excessive timeout
    - Try: `mcp__automagik_workflows__run_workflow(workflow_name="builder", message="Test", timeout=20000)`
    - Expected: Should return validation error about timeout limit

44. **EH-05**: Test invalid session ID format
    - Try: `mcp__automagik_workflows__run_workflow(workflow_name="builder", message="Test", session_id="invalid-uuid")`
    - Expected: Should return validation error about UUID format

45. **EH-06**: Test invalid repository URL
    - Try: `mcp__automagik_workflows__run_workflow(workflow_name="builder", message="Test", repository_url="not-a-url")`
    - Expected: Should return validation error about URL format

### Phase 5: Performance Tests (2 tests)

46. **PF-01**: Sequential workflow performance
    - Execute 5 guardian workflows sequentially
    - Measure total time and resource usage
    - Check for performance degradation

47. **PF-02**: Concurrent workflow performance  
    - Start 3 workflows simultaneously (guardian, builder, surgeon)
    - Monitor for conflicts and resource usage
    - Validate concurrent execution

### Phase 6: Integration Tests (3 tests)

48. **IT-01**: Complete feature development lifecycle
    - Execute: lina → builder → guardian → shipper sequence
    - Validate each phase builds on previous
    - Check end-to-end integration

49. **IT-02**: Bug fix cycle
    - Execute: brain → surgeon → guardian sequence
    - Validate issue identification and resolution
    - Check fix validation cycle

50. **IT-03**: Documentation cycle
    - Execute: builder → brain → guardian sequence
    - Validate documentation creation and testing
    - Check knowledge management cycle

## What to Do With Results

For **each test**, document:

### Test Result Template
```markdown
## Test [ID]: [Name]
- **Status**: ✅ PASSED / ❌ FAILED / ⚠️ ERROR / ⏰ TIMEOUT
- **Execution Time**: [X] seconds
- **Turns Used**: [X] / [max_turns]
- **Cost**: $[X.XXXX]
- **Tokens**: [X] total
- **Tools Used**: [list]
- **Files Created**: [list]
- **Git Operations**: [commits/PRs]
- **Error Message**: [if failed]
- **Notes**: [observations]
```

### Monitoring During Execution

For each test:
1. **Start the workflow** with the specified parameters
2. **Monitor progress** using `mcp__automagik_workflows__get_workflow_status(run_id, detailed=true)`
3. **Wait appropriately** using `mcp__wait__*` tools
4. **Document the outcome** immediately after completion
5. **Move to next test** systematically

### Final Report Structure

After completing ALL 50 tests, generate this report:

```markdown
# QA Testing Report - Claude Code Workflow System

## Executive Summary
- **Total Tests**: 50
- **Passed**: [X]
- **Failed**: [X] 
- **Errors**: [X]
- **Timeouts**: [X]
- **Overall Success Rate**: [X]%

## Critical Issues Found
[List any workflow failures or critical problems that would prevent safe PR merging]

## What Works Well
[List workflows and features that work reliably]

## What Needs Attention  
[List workflows and features that have issues]

## Workflow-Specific Results
### Guardian (Testing) - [X]/[Y] tests passed
### Builder (Implementation) - [X]/[Y] tests passed  
### Surgeon (Fixes) - [X]/[Y] tests passed
### Genie (Orchestration) - [X]/[Y] tests passed
### Shipper (Deployment) - [X]/[Y] tests passed
### Lina (Linear Integration) - [X]/[Y] tests passed
### Brain (Knowledge) - [X]/[Y] tests passed

## Feature Coverage Results
### Basic Functionality: [X]% success
### Repository Operations: [X]% success
### Persistence: [X]% success
### Session Management: [X]% success  
### Error Handling: [X]% success
### Performance: [X]% success
### Integration: [X]% success

## Recommendations
### ✅ Safe to Merge PRs if:
[List conditions when it's safe]

### ⚠️ Proceed with Caution if:
[List conditions requiring careful review]

### ❌ Do NOT Merge PRs if:
[List conditions that block merging]

## Detailed Test Results
[Include all 50 individual test results]
```

## Success Criteria for Safe PR Merging

✅ **GREEN LIGHT** - Safe to merge PRs if:
- Basic Functionality: 85%+ success rate
- Repository Operations: 80%+ success rate
- Error Handling: 100% proper error responses
- No critical workflow failures
- All 7 workflows have at least basic functionality

⚠️ **YELLOW LIGHT** - Proceed with caution if:
- Basic Functionality: 70-84% success rate
- Some advanced features failing
- Non-critical error handling issues
- Performance concerns but no failures

❌ **RED LIGHT** - DO NOT merge PRs if:
- Basic Functionality: <70% success rate
- Any workflow completely broken
- Critical error handling failures
- System instability or crashes
- Data corruption or workspace issues

Execute this systematically and provide the final report for safe PR merging decisions!