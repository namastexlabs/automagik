# Claude Code Workflow Manual Testing Plan

## 🎯 Objective
Manually test the Claude Code workflow system through API endpoints to verify functionality, understand behavior, and validate the integration without using automated scripts.

## 📋 Test Prerequisites

### 1. Environment Setup
- [ ] Automagik Agents server running (`make dev` or `AM_FORCE_DEV_ENV=1 uv run python -m src --reload`)
- [ ] Claude CLI installed and authenticated (`~/.claude/.credentials.json` exists)
- [ ] API authentication token available (if auth is enabled)
- [ ] Git repository initialized in workspace
- [ ] Docker daemon running (for Docker mode testing)

### 2. Testing Tools
- **API Client**: Postman, Insomnia, or curl
- **Log Monitoring**: `tail -f logs/server.log` or `make logs FOLLOW=1`
- **Database Client**: For checking session records
- **Git Client**: For verifying commits

## 🧪 Test Scenarios

### Scenario 1: Basic Workflow Health Check

**1.1 Check Available Workflows**
```http
GET http://localhost:8881/api/v1/agent/claude-code/workflows
```

Expected Response:
```json
{
  "workflows": [
    {
      "name": "architect",
      "description": "System design and architecture",
      "has_prompt": true,
      "allowed_tools": ["Read", "Write", "Linear", "Memory"]
    },
    {
      "name": "implement",
      "description": "Feature implementation",
      "has_prompt": true,
      "allowed_tools": ["Task", "Bash", "Edit", "Git", "Memory"]
    },
    // ... other workflows
  ]
}
```

**1.2 Health Check**
```http
GET http://localhost:8881/api/v1/agent/claude-code/health
```

Expected Response:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "mode": "docker", // or "local"
  "claude_cli_available": true,
  "workspace_accessible": true
}
```

### Scenario 2: Simple ARCHITECT Workflow Execution

**2.1 Start ARCHITECT Workflow**
```http
POST http://localhost:8881/api/v1/agent/claude-code/architect/run
Content-Type: application/json

{
  "message": "Design a simple TODO API with user authentication. Create ARCHITECTURE.md with the design.",
  "max_turns": 20,
  "git_branch": "test-architect-todo-api"
}
```

Expected Response:
```json
{
  "run_id": "architect-1234567890",
  "workflow": "architect",
  "status": "started",
  "session_id": "session-abc123",
  "started_at": "2025-01-06T10:00:00Z"
}
```

**2.2 Monitor Progress**
```http
GET http://localhost:8881/api/v1/agent/claude-code/run/architect-1234567890/status
```

Progressive Status Responses:
```json
// Initial
{
  "run_id": "architect-1234567890",
  "status": "running",
  "progress": {
    "turn": 3,
    "max_turns": 20,
    "last_action": "Creating ARCHITECTURE.md file"
  }
}

// Completed
{
  "run_id": "architect-1234567890",
  "status": "completed",
  "result": {
    "success": true,
    "files_created": ["ARCHITECTURE.md", "DECISIONS.md"],
    "files_modified": [],
    "git_commits": ["feat: design TODO API architecture"],
    "summary": "Designed TODO API with JWT authentication"
  },
  "completed_at": "2025-01-06T10:05:00Z",
  "duration_seconds": 300
}
```

### Scenario 3: IMPLEMENT Workflow with Session Continuity

**3.1 Start IMPLEMENT Using Previous Session**
```http
POST http://localhost:8881/api/v1/agent/claude-code/implement/run
Content-Type: application/json

{
  "message": "Implement the TODO API based on ARCHITECTURE.md. Focus on the user model and authentication endpoints first.",
  "session_id": "session-abc123",  // Reuse session from ARCHITECT
  "max_turns": 40,
  "git_branch": "test-architect-todo-api"
}
```

**3.2 Real-time Monitoring via Logs**
```bash
# In another terminal
tail -f logs/server.log | grep "claude-code"

# Expected log patterns:
# [INFO] Starting Claude Code workflow: implement
# [INFO] Executor: DockerExecutor
# [INFO] Container ID: claude-code-implement-xyz
# [INFO] Claude action: Reading ARCHITECTURE.md
# [INFO] Claude action: Creating src/models/user.py
# [INFO] Claude action: Running tests
```

### Scenario 4: Error Handling and Recovery

**4.1 Test with Invalid Workflow**
```http
POST http://localhost:8881/api/v1/agent/claude-code/invalid-workflow/run
Content-Type: application/json

{
  "message": "This should fail"
}
```

Expected Response:
```json
{
  "detail": "Workflow 'invalid-workflow' not found"
}
```

**4.2 Test Timeout Behavior**
```http
POST http://localhost:8881/api/v1/agent/claude-code/implement/run
Content-Type: application/json

{
  "message": "Implement something complex",
  "max_turns": 100,
  "timeout": 60  // Very short timeout
}
```

Monitor for timeout handling in status checks.

### Scenario 5: Complex Multi-Workflow Epic

**5.1 Execute Full Development Cycle**

1. **ARCHITECT Phase**
```http
POST http://localhost:8881/api/v1/agent/claude-code/architect/run
{
  "message": "Design a Discord bot integration for automagik-agents. Include async message handling, memory persistence, and rate limiting.",
  "max_turns": 30
}
```

2. **IMPLEMENT Phase** (after ARCHITECT completes)
```http
POST http://localhost:8881/api/v1/agent/claude-code/implement/run
{
  "message": "Implement the Discord bot based on ARCHITECTURE.md. Create DiscordAgent extending AutomagikAgent.",
  "session_id": "[from-architect-response]",
  "max_turns": 50
}
```

3. **TEST Phase**
```http
POST http://localhost:8881/api/v1/agent/claude-code/test/run
{
  "message": "Create comprehensive tests for the Discord bot implementation. Test async operations, memory integration, and error handling.",
  "session_id": "[same-session]",
  "max_turns": 40
}
```

4. **REVIEW Phase**
```http
POST http://localhost:8881/api/v1/agent/claude-code/review/run
{
  "message": "Review the Discord bot implementation for code quality, security, and adherence to automagik-agents patterns.",
  "session_id": "[same-session]",
  "max_turns": 20
}
```

### Scenario 6: Docker vs Local Mode Testing

**6.1 Force Local Mode** (if configured)
```bash
# Set environment variable
export CLAUDE_CODE_MODE=local
# Restart server
```

**6.2 Compare Execution**
Run same workflow in both modes and compare:
- Execution speed
- Resource usage
- File isolation
- Cleanup behavior

### Scenario 7: Memory Integration Testing

**7.1 Workflow with Memory Search**
```http
POST http://localhost:8881/api/v1/agent/claude-code/implement/run
{
  "message": "Search memory for Discord integration patterns before implementing. Use any found patterns in the implementation.",
  "max_turns": 30
}
```

Monitor logs for memory tool usage:
```
[INFO] Claude action: Searching memory for "Discord integration patterns"
[INFO] Claude action: Found pattern "async-message-handler"
```

### Scenario 8: Breaking Change Detection

**8.1 Trigger Breaking Change**
```http
POST http://localhost:8881/api/v1/agent/claude-code/refactor/run
{
  "message": "Refactor the API to change all endpoints from /api/v1/ to /api/v2/. Update all references.",
  "max_turns": 30
}
```

Expected: Workflow should detect breaking change and request human approval.

## 📊 Test Verification Checklist

### For Each Test Scenario:

1. **Request/Response Validation**
   - [ ] Correct HTTP status codes
   - [ ] Proper JSON structure
   - [ ] Meaningful error messages
   - [ ] Unique run_id generation

2. **Execution Monitoring**
   - [ ] Real-time progress updates
   - [ ] Accurate turn counting
   - [ ] Proper status transitions
   - [ ] Log entries correlation

3. **File System Changes**
   - [ ] Files created/modified as expected
   - [ ] Correct file permissions
   - [ ] Git commits created
   - [ ] Branch management

4. **Session Persistence**
   - [ ] Session continuity works
   - [ ] Context maintained between workflows
   - [ ] Database records created

5. **Resource Management**
   - [ ] Containers cleaned up (Docker mode)
   - [ ] Temporary files removed (Local mode)
   - [ ] No resource leaks

6. **Error Handling**
   - [ ] Graceful failure modes
   - [ ] Detailed error information
   - [ ] Recovery possibilities

## 🔍 Advanced Testing

### Load Testing
1. Start multiple workflows simultaneously
2. Monitor system resources
3. Check for race conditions
4. Verify queue management

### Integration Testing
1. Test with real Linear API integration
2. Verify Slack notifications
3. Check memory system updates
4. Validate Git operations

### Security Testing
1. Test with malicious prompts
2. Verify file access boundaries
3. Check container isolation
4. Validate authentication

## 📈 Performance Metrics to Track

1. **Workflow Execution Times**
   - ARCHITECT: Expected 2-5 minutes
   - IMPLEMENT: Expected 5-15 minutes
   - TEST: Expected 5-10 minutes

2. **Resource Usage**
   - CPU usage per workflow
   - Memory consumption
   - Disk I/O patterns

3. **Success Rates**
   - Completion percentage
   - Error frequency
   - Timeout occurrences

## 🎯 Expected Outcomes

### Successful Test Indicators:
1. All workflows execute without manual intervention
2. Progress tracking provides meaningful updates
3. File changes match workflow purposes
4. Session continuity enables complex epics
5. Error handling is graceful and informative

### Common Issues to Watch For:
1. Claude CLI authentication failures
2. Docker permission issues
3. Git configuration problems
4. Memory tool access errors
5. Timeout configurations

## 📝 Test Report Template

```markdown
## Claude Code Workflow Test Report

**Date**: [Date]
**Tester**: [Name]
**Environment**: [Docker/Local]

### Summary
- Total Workflows Tested: X/9
- Success Rate: X%
- Average Execution Time: X minutes

### Detailed Results

#### ARCHITECT Workflow
- Status: ✅ Passed / ❌ Failed
- Execution Time: X seconds
- Issues Found: [List any]
- Files Created: [List]

[Repeat for each workflow]

### Recommendations
1. [Improvement suggestion 1]
2. [Improvement suggestion 2]

### Next Steps
1. [Action item 1]
2. [Action item 2]
```

## 🚀 Quick Test Commands

### Using curl:
```bash
# List workflows
curl http://localhost:8881/api/v1/agent/claude-code/workflows

# Start architect workflow
curl -X POST http://localhost:8881/api/v1/agent/claude-code/architect/run \
  -H "Content-Type: application/json" \
  -d '{"message": "Design a simple TODO API", "max_turns": 20}'

# Check status
curl http://localhost:8881/api/v1/agent/claude-code/run/[run_id]/status
```

### Using HTTPie:
```bash
# List workflows
http GET localhost:8881/api/v1/agent/claude-code/workflows

# Start workflow
http POST localhost:8881/api/v1/agent/claude-code/architect/run \
  message="Design a simple TODO API" max_turns=20

# Check status
http GET localhost:8881/api/v1/agent/claude-code/run/[run_id]/status
```

This test plan provides a comprehensive approach to manually testing the Claude Code workflow system through API endpoints, enabling validation of all major features and edge cases.