# Agentic QA Test Prompts for Claude Code Workflows

## Overview

This document provides systematic test prompts for agents to comprehensively validate the Claude Code workflow system. Each prompt is designed for agentic execution using MCP workflow tools, ensuring 100% coverage of all workflow combinations and parameters.

## Test Execution Instructions for Agents

### How to Execute These Tests
1. Use `mcp__automagik_workflows__run_workflow()` to execute each test
2. Monitor with `mcp__automagik_workflows__get_workflow_status()`
3. Document results systematically
4. Use `mcp__wait__*` tools for optimal timing
5. Validate against expected outcomes

### Test Result Template
For each test, document:
- **Test ID**: (e.g., BF-01)
- **Execution Time**: How long it took
- **Status**: passed/failed/error/timeout
- **Turns Used**: Number of conversation turns
- **Tools Used**: List of tools utilized
- **Cost**: USD cost incurred
- **Tokens**: Total tokens consumed
- **Files Created/Modified**: List of artifacts
- **Git Operations**: Commits, branches, PRs
- **Issues Found**: Any problems encountered
- **Validation**: Does it meet requirements?

---

## Basic Functionality Test Prompts (BF-01 to BF-21)

### Simple Execution Tests (BF-01 to BF-07)

**BF-01: Guardian Basic Health Check**
```
Execute this test using mcp__automagik_workflows__run_workflow():

workflow_name: "guardian"
message: "Perform a basic health check on the current codebase. Check for common issues like import errors, syntax problems, and basic security vulnerabilities. Provide a clear summary of findings."
session_name: "qa_guardian_basic_health"
max_turns: 5

Expected outcomes:
- Should complete successfully
- Generate health report
- Identify any obvious issues
- Provide actionable recommendations
- Complete within 5 turns
```

**BF-02: Surgeon Simple Fix**
```
Execute this test using mcp__automagik_workflows__run_workflow():

workflow_name: "surgeon"
message: "Scan the codebase for any simple syntax errors, unused imports, or basic code quality issues. Fix what you find with minimal, surgical changes."
session_name: "qa_surgeon_simple_fix"
max_turns: 5

Expected outcomes:
- Identify and fix simple issues
- Make minimal, targeted changes
- Maintain code functionality
- Document changes made
- No breaking changes
```

**BF-03: Brain Knowledge Storage**
```
Execute this test using mcp__automagik_workflows__run_workflow():

workflow_name: "brain"
message: "Analyze the current project structure and store key knowledge about Python best practices, architectural patterns, and development workflows used in this codebase."
session_name: "qa_brain_knowledge_storage"
max_turns: 5

Expected outcomes:
- Extract architectural patterns
- Store development workflows
- Identify best practices
- Create knowledge documentation
- Use memory tools effectively
```

**BF-04: Genie Simple Coordination**
```
Execute this test using mcp__automagik_workflows__run_workflow():

workflow_name: "genie"
message: "Coordinate a simple documentation update task. Review existing documentation and improve one specific area (like README, setup instructions, or code comments)."
session_name: "qa_genie_simple_coordination"
max_turns: 5

Expected outcomes:
- Identify documentation gaps
- Coordinate improvement task
- Use other workflows if needed
- Improve documentation quality
- Show orchestration capability
```

**BF-05: Shipper Deployment Preparation**
```
Execute this test using mcp__automagik_workflows__run_workflow():

workflow_name: "shipper"
message: "Prepare a basic deployment checklist for this project. Review current configuration, identify deployment requirements, and create a simple deployment guide."
session_name: "qa_shipper_deployment_prep"
max_turns: 5

Expected outcomes:
- Analyze deployment needs
- Create deployment checklist
- Identify configuration requirements
- Document deployment process
- Consider production readiness
```

**BF-06: Lina Linear Integration**
```
Execute this test using mcp__automagik_workflows__run_workflow():

workflow_name: "lina"
message: "Create a simple Linear issue for tracking QA test progress. Include relevant details about the testing initiative and set appropriate labels."
session_name: "qa_lina_linear_integration"
max_turns: 5

Expected outcomes:
- Connect to Linear workspace
- Create well-structured issue
- Set appropriate labels/status
- Include relevant details
- Demonstrate Linear integration
```

**BF-07: Builder Simple Implementation**
```
Execute this test using mcp__automagik_workflows__run_workflow():

workflow_name: "builder"
message: "Create a simple 'hello world' utility function with proper documentation, type hints, and a basic test. Follow Python best practices."
session_name: "qa_builder_hello_world"
max_turns: 5

Expected outcomes:
- Create well-structured function
- Include type hints and docstrings
- Write accompanying test
- Follow coding standards
- Generate clean, working code
```

### Complex Task Tests (BF-08 to BF-14)

**BF-08: Guardian Security Audit**
```
Execute this test using mcp__automagik_workflows__run_workflow():

workflow_name: "guardian"
message: "Perform a comprehensive security audit of the authentication and API systems. Check for vulnerabilities, insecure configurations, and security best practices compliance."
session_name: "qa_guardian_security_audit"
max_turns: 15

Expected outcomes:
- Thorough security analysis
- Identify vulnerabilities
- Check authentication systems
- Validate API security
- Provide detailed recommendations
```

**BF-09: Surgeon Complex Refactoring**
```
Execute this test using mcp__automagik_workflows__run_workflow():

workflow_name: "surgeon"
message: "Identify and refactor any complex code modules that could benefit from improved maintainability. Focus on reducing complexity while preserving functionality."
session_name: "qa_surgeon_complex_refactor"
max_turns: 15

Expected outcomes:
- Identify complex code
- Improve maintainability
- Preserve all functionality
- Add tests if needed
- Document changes
```

**BF-10: Brain Architecture Analysis**
```
Execute this test using mcp__automagik_workflows__run_workflow():

workflow_name: "brain"
message: "Conduct a deep analysis of the project architecture. Store comprehensive knowledge about design patterns, component relationships, and architectural decisions."
session_name: "qa_brain_architecture_analysis"
max_turns: 15

Expected outcomes:
- Map system architecture
- Identify design patterns
- Document relationships
- Store architectural knowledge
- Create architectural diagrams
```

**BF-11: Genie Full Lifecycle Orchestration**
```
Execute this test using mcp__automagik_workflows__run_workflow():

workflow_name: "genie"
message: "Orchestrate a complete feature development lifecycle for a small utility (like a configuration validator). Coordinate planning, implementation, testing, and documentation."
session_name: "qa_genie_full_lifecycle"
max_turns: 20

Expected outcomes:
- Coordinate multiple workflows
- Manage dependencies
- Ensure quality gates
- Complete feature development
- Demonstrate orchestration
```

**BF-12: Shipper CI/CD Setup**
```
Execute this test using mcp__automagik_workflows__run_workflow():

workflow_name: "shipper"
message: "Set up comprehensive CI/CD pipeline configuration including testing, linting, security scanning, and deployment automation."
session_name: "qa_shipper_cicd_setup"
max_turns: 15

Expected outcomes:
- Configure CI/CD pipeline
- Include quality gates
- Set up automation
- Document deployment process
- Test pipeline configuration
```

**BF-13: Lina Project Synchronization**
```
Execute this test using mcp__automagik_workflows__run_workflow():

workflow_name: "lina"
message: "Synchronize current project status with Linear workspace. Update existing issues, create missing tasks, and ensure project tracking is current."
session_name: "qa_lina_project_sync"
max_turns: 15

Expected outcomes:
- Audit current project state
- Update Linear workspace
- Create missing tasks
- Synchronize status
- Maintain project visibility
```

**BF-14: Builder REST API Implementation**
```
Execute this test using mcp__automagik_workflows__run_workflow():

workflow_name: "builder"
message: "Implement a comprehensive REST API endpoint with authentication, input validation, error handling, and comprehensive documentation. Include tests."
session_name: "qa_builder_rest_api"
max_turns: 15

Expected outcomes:
- Create complete API endpoint
- Implement authentication
- Add input validation
- Include error handling
- Write comprehensive tests
```

### Turn Limit Tests (BF-15 to BF-18)

**BF-15: Builder with Turn Constraint**
```
Execute this test using mcp__automagik_workflows__run_workflow():

workflow_name: "builder"
message: "Create a complex data processing pipeline with multiple stages. Work efficiently within the turn limit."
session_name: "qa_builder_turn_limit"
max_turns: 3

Expected outcomes:
- Reach maximum turns (3)
- Make meaningful progress
- Handle turn limit gracefully
- Prioritize most important features
- Status should indicate max_turns_reached
```

**BF-16: Guardian Exhaustive Testing**
```
Execute this test using mcp__automagik_workflows__run_workflow():

workflow_name: "guardian"
message: "Run an exhaustive test suite covering unit tests, integration tests, security tests, and performance validation."
session_name: "qa_guardian_exhaustive"
max_turns: 10

Expected outcomes:
- Complete within 10 turns
- Run comprehensive tests
- Generate detailed reports
- Identify all issues
- Provide quality assessment
```

**BF-17: Surgeon Multiple Issues**
```
Execute this test using mcp__automagik_workflows__run_workflow():

workflow_name: "surgeon"
message: "Identify and fix multiple interconnected code issues including performance problems, security vulnerabilities, and maintainability concerns."
session_name: "qa_surgeon_multiple_issues"
max_turns: 5

Expected outcomes:
- Work efficiently within 5 turns
- Prioritize critical issues
- Fix multiple problems
- Document all changes
- Maintain system stability
```

**BF-18: Genie Unlimited Coordination**
```
Execute this test using mcp__automagik_workflows__run_workflow():

workflow_name: "genie"
message: "Coordinate a multi-step workflow optimization project with no turn restrictions. Take the time needed to do it properly."
session_name: "qa_genie_unlimited"
max_turns: null

Expected outcomes:
- Use as many turns as needed
- Coordinate multiple workflows
- Optimize comprehensively
- Achieve high quality results
- Demonstrate unlimited capability
```

### Timeout Tests (BF-19 to BF-21)

**BF-19: Shipper Production Deployment**
```
Execute this test using mcp__automagik_workflows__run_workflow():

workflow_name: "shipper"
message: "Test complete production deployment process including environment setup, configuration validation, and deployment verification."
session_name: "qa_shipper_production"
timeout: 3600

Expected outcomes:
- Complete within 1 hour
- Handle production complexity
- Validate deployment
- Ensure system stability
- Document deployment process
```

**BF-20: Brain Large Knowledge Processing**
```
Execute this test using mcp__automagik_workflows__run_workflow():

workflow_name: "brain"
message: "Process and organize a large knowledge base including all project documentation, code patterns, and architectural decisions."
session_name: "qa_brain_large_processing"
timeout: 7200

Expected outcomes:
- Handle large data processing
- Complete within 2 hours
- Organize knowledge effectively
- Create comprehensive index
- Maintain performance
```

**BF-21: Builder Quick Prototype**
```
Execute this test using mcp__automagik_workflows__run_workflow():

workflow_name: "builder"
message: "Create a quick prototype implementation under time pressure. Focus on core functionality and rapid delivery."
session_name: "qa_builder_quick_prototype"
timeout: 300

Expected outcomes:
- Work under time pressure
- Deliver core functionality
- Handle timeout gracefully
- Prioritize essential features
- May timeout but show progress
```

---

## Repository Source Test Prompts (RS-01 to RS-09)

### Local Repository Tests (RS-01 to RS-03)

**RS-01: Local Repository Work**
```
Execute this test using mcp__automagik_workflows__run_workflow():

workflow_name: "builder"
message: "Work in the current repository to create a simple utility function. Test that local repository operations work correctly."
session_name: "qa_local_repo_work"
max_turns: 5

Expected outcomes:
- Work in current repository
- Create utility function
- Commit changes locally
- No repository cloning
- Use existing workspace
```

**RS-02: Specific Branch Work**
```
Execute this test using mcp__automagik_workflows__run_workflow():

workflow_name: "guardian"
message: "Run tests specifically on the main branch. Validate branch-specific operations work correctly."
session_name: "qa_specific_branch"
git_branch: "main"
max_turns: 8

Expected outcomes:
- Work on specified branch
- Run branch-specific tests
- Validate git operations
- Respect branch constraints
- Generate branch-specific report
```

**RS-03: Local Branch Operations**
```
Execute this test using mcp__automagik_workflows__run_workflow():

workflow_name: "surgeon"
message: "Fix any issues found on the main branch of the current repository. Test local git operations."
session_name: "qa_local_branch_ops"
git_branch: "main"
max_turns: 6

Expected outcomes:
- Work on specified branch
- Fix identified issues
- Perform git operations
- Commit fixes locally
- Maintain branch integrity
```

### Git Integration Tests (RS-07 to RS-09)

**RS-07: Automatic PR Creation**
```
Execute this test using mcp__automagik_workflows__run_workflow():

workflow_name: "builder"
message: "Implement a new feature and automatically create a pull request when completed successfully."
session_name: "qa_auto_pr_creation"
create_pr_on_success: true
pr_title: "feat: Add new feature from QA test"
pr_body: "This PR was automatically created by the QA testing system to validate PR creation functionality."
max_turns: 8

Expected outcomes:
- Implement feature successfully
- Automatically create PR
- Use specified PR title and body
- Link to implementation
- Show PR creation capability
```

**RS-08: Bug Fix PR Creation**
```
Execute this test using mcp__automagik_workflows__run_workflow():

workflow_name: "surgeon"
message: "Fix a critical bug and create an automatic pull request for the fix."
session_name: "qa_bugfix_pr"
create_pr_on_success: true
pr_title: "fix: Critical bug resolution from QA"
pr_body: "Automated bug fix PR created during QA testing to validate surgical fix and PR creation workflow."
max_turns: 6

Expected outcomes:
- Identify and fix bug
- Create PR automatically
- Use bug fix conventions
- Document fix properly
- Validate PR workflow
```

**RS-09: No PR Deployment**
```
Execute this test using mcp__automagik_workflows__run_workflow():

workflow_name: "shipper"
message: "Prepare deployment configuration without creating a pull request. Test deployment without PR creation."
session_name: "qa_no_pr_deployment"
create_pr_on_success: false
max_turns: 5

Expected outcomes:
- Prepare deployment
- No PR creation
- Direct deployment prep
- Validate no-PR workflow
- Focus on deployment artifacts
```

---

## Persistence Test Prompts (PS-01 to PS-09)

### Persistent Workspace Tests (PS-01 to PS-03)

**PS-01: Persistent Workspace Creation**
```
Execute this test using mcp__automagik_workflows__run_workflow():

workflow_name: "builder"
message: "Create a utility function that should be retained in persistent workspace after completion. Test workspace persistence."
session_name: "persistent-session-1"
persistent: true
max_turns: 6

Expected outcomes:
- Create in persistent workspace
- Files remain after completion
- Workspace is retained
- Can be accessed later
- Persistence confirmed
```

**PS-02: Persistent Test Environment**
```
Execute this test using mcp__automagik_workflows__run_workflow():

workflow_name: "guardian"
message: "Set up a persistent test environment with configuration files that should remain available for future testing."
session_name: "test-environment"
persistent: true
max_turns: 8

Expected outcomes:
- Create test environment
- Configuration persists
- Environment reusable
- Files remain accessible
- Persistence validated
```

### Temporary Workspace Tests (PS-04 to PS-06)

**PS-04: Temporary Workspace Cleanup**
```
Execute this test using mcp__automagik_workflows__run_workflow():

workflow_name: "builder"
message: "Create a temporary function that should be cleaned up after completion. Test temporary workspace cleanup."
session_name: "temp-session-1"
persistent: false
max_turns: 5

Expected outcomes:
- Work in temporary workspace
- Files cleaned after completion
- No persistence
- Workspace removed
- Cleanup validated
```

**PS-05: Temporary Test Environment**
```
Execute this test using mcp__automagik_workflows__run_workflow():

workflow_name: "guardian"
message: "Run tests in temporary environment that cleans up automatically after completion."
session_name: "temp-test"
persistent: false
max_turns: 6

Expected outcomes:
- Use temporary environment
- Run tests successfully
- Environment cleaned up
- No files persist
- Temporary nature confirmed
```

---

## Session Management Test Prompts (SM-01 to SM-09)

### New Session Tests (SM-01 to SM-03)

**SM-01: New Session with User Tracking**
```
Execute this test using mcp__automagik_workflows__run_workflow():

workflow_name: "builder"
message: "Create a new session with user tracking to test session management and user association."
session_name: "new-feature-dev"
user_id: "user-123"
max_turns: 6

Expected outcomes:
- Create new session
- Associate with user
- Track session properly
- Maintain user context
- Session management works
```

**SM-02: Anonymous Session Creation**
```
Execute this test using mcp__automagik_workflows__run_workflow():

workflow_name: "guardian"
message: "Create anonymous session without user tracking to test anonymous session handling."
session_name: "qa-session"
max_turns: 5

Expected outcomes:
- Create anonymous session
- No user association
- Session works independently
- Anonymous handling correct
- Basic session functionality
```

### Session Continuation Tests (SM-04 to SM-06)

**SM-04: Session Continuation by ID**
```
First, run a workflow and note the session_id from the response.
Then execute this test using the obtained session_id:

Execute this test using mcp__automagik_workflows__run_workflow():

workflow_name: "builder"
message: "Continue the previous session and build upon the existing work. Test session continuation."
session_id: "{obtained_session_id}"
max_turns: 8

Expected outcomes:
- Continue existing session
- Build on previous work
- Maintain session context
- Access previous files
- Session continuation works
```

**SM-05: Session Continuation by Name**
```
After running SM-01, execute this test:

Execute this test using mcp__automagik_workflows__run_workflow():

workflow_name: "guardian"
message: "Find and continue the 'new-feature-dev' session to add tests to the previous work."
session_name: "new-feature-dev"
max_turns: 6

Expected outcomes:
- Find existing session by name
- Continue previous work
- Add complementary work
- Maintain session state
- Name-based continuation works
```

---

## Error Handling Test Prompts (EH-01 to EH-15)

### Input Validation Tests (EH-01 to EH-06)

**EH-01: Empty Message Test**
```
Execute this test to validate error handling:

Try to execute: mcp__automagik_workflows__run_workflow()
workflow_name: "builder"
message: ""

Expected outcomes:
- Should return validation error
- Error message about required message
- No workflow execution
- Proper error handling
- Clear error description
```

**EH-02: Invalid Workflow Name**
```
Execute this test to validate error handling:

Try to execute: mcp__automagik_workflows__run_workflow()
workflow_name: "invalid-workflow"
message: "Test invalid workflow name handling"

Expected outcomes:
- Should return 404 error
- List available workflows
- Clear error message
- No execution attempted
- Helpful error guidance
```

**EH-03: Excessive Turn Limit**
```
Execute this test to validate error handling:

Try to execute: mcp__automagik_workflows__run_workflow()
workflow_name: "builder"
message: "Test turn limit validation"
max_turns: 250

Expected outcomes:
- Should return validation error
- Error about turn limit exceeded
- Maximum allowed turns mentioned
- No workflow execution
- Clear boundary enforcement
```

---

## Performance Test Prompts (PF-01 to PF-06)

### Scalability Tests (PF-01 to PF-03)

**PF-01: Sequential Workflow Execution**
```
Execute 10 workflows sequentially and measure performance:

For i in range(10):
  Execute: mcp__automagik_workflows__run_workflow()
  workflow_name: "guardian"
  message: f"Quick health check #{i+1} for performance testing"
  session_name: f"perf_test_sequential_{i+1}"
  max_turns: 3

Expected outcomes:
- All 10 workflows complete
- Measure total execution time
- Check resource usage
- Validate system stability
- No performance degradation
```

**PF-02: Concurrent Workflow Execution**
```
Execute 5 workflows concurrently and measure performance:

Start all 5 simultaneously:
- guardian: "Health check A"
- builder: "Create function A"  
- surgeon: "Fix issues A"
- brain: "Store knowledge A"
- shipper: "Prep deployment A"

Expected outcomes:
- All 5 workflows execute
- Proper resource management
- No conflicts between workflows
- Concurrent execution successful
- System handles load
```

---

## Integration Test Prompts (IT-01 to IT-06)

### End-to-End Workflow Tests (IT-01 to IT-03)

**IT-01: Complete Feature Development Lifecycle**
```
Execute complete feature development sequence:

1. Execute: workflow_name: "lina"
   message: "Create Linear epic for feature development lifecycle test"
   
2. Wait for completion, then execute: workflow_name: "builder"  
   message: "Implement the feature described in the Linear epic"
   
3. Wait for completion, then execute: workflow_name: "guardian"
   message: "Test and validate the implemented feature"
   
4. Wait for completion, then execute: workflow_name: "shipper"
   message: "Prepare deployment for the tested feature"

Expected outcomes:
- Complete end-to-end lifecycle
- Each phase builds on previous
- Quality gates maintained
- Full feature delivery
- Integration successful
```

**IT-02: Bug Fix Cycle**
```
Execute complete bug fix sequence:

1. Execute: workflow_name: "brain"
   message: "Analyze codebase to identify potential bugs or issues"
   
2. Wait for completion, then execute: workflow_name: "surgeon"
   message: "Fix the issues identified by brain analysis"
   
3. Wait for completion, then execute: workflow_name: "guardian"
   message: "Validate that the fixes are correct and don't break anything"

Expected outcomes:
- Complete bug identification and fix
- Proper issue resolution
- Validation of fixes
- Quality maintained
- Bug fix cycle works
```

---

## Test Execution Framework for Agents

### Systematic Test Execution Approach

1. **Preparation Phase**
   - Review all test prompts
   - Understand expected outcomes
   - Prepare result documentation
   - Set up monitoring

2. **Execution Phase**
   - Execute tests systematically
   - Monitor progress continuously
   - Document results immediately
   - Handle failures gracefully

3. **Validation Phase**
   - Compare actual vs expected outcomes
   - Identify any discrepancies
   - Document issues found
   - Calculate success rates

4. **Reporting Phase**
   - Generate comprehensive report
   - Include all test results
   - Highlight key findings
   - Provide recommendations

### Success Criteria

Each test category should achieve:
- **Basic Functionality**: 90%+ success rate
- **Repository Operations**: 85%+ success rate  
- **Persistence**: 95%+ success rate
- **Session Management**: 90%+ success rate
- **Error Handling**: 100% proper error responses
- **Performance**: No degradation under load
- **Integration**: 85%+ end-to-end success

This systematic approach ensures comprehensive validation of the Claude Code workflow system through agentic testing.