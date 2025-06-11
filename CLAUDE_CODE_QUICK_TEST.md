# Claude Code Workflow - Quick Test Reference

## 🚀 Quick Start Commands

### 1. Start the Server
```bash
# Development mode with auto-reload
make dev

# OR manually
AM_FORCE_DEV_ENV=1 uv run python -m src --reload
```

### 2. Monitor Logs (in another terminal)
```bash
# Follow server logs
make logs FOLLOW=1

# OR
tail -f logs/server.log | grep -E "(claude-code|workflow)"
```

## 📋 Test Commands (using curl)

### List Available Workflows
```bash
curl -X GET http://localhost:8881/api/v1/agent/claude-code/workflows \
  -H "Authorization: Bearer test-key"
```

### Check Health
```bash
curl -X GET http://localhost:8881/api/v1/agent/claude-code/health \
  -H "Authorization: Bearer test-key"
```

### Run ARCHITECT Workflow
```bash
# Start the workflow
curl -X POST http://localhost:8881/api/v1/agent/claude-code/architect/run \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer test-key" \
  -d '{
    "message": "Design a simple TODO API with JWT authentication. Create ARCHITECTURE.md with the design.",
    "max_turns": 30,
    "git_branch": "test-todo-api"
  }'

# Save the run_id from response, then check status
curl -X GET http://localhost:8881/api/v1/agent/claude-code/run/[RUN_ID]/status \
  -H "Authorization: Bearer test-key"
```

### Run IMPLEMENT Workflow (using session from ARCHITECT)
```bash
# Use the session_id from ARCHITECT run
curl -X POST http://localhost:8881/api/v1/agent/claude-code/implement/run \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer test-key" \
  -d '{
    "message": "Implement the TODO API based on ARCHITECTURE.md",
    "session_id": "[SESSION_ID_FROM_ARCHITECT]",
    "max_turns": 50,
    "git_branch": "test-todo-api"
  }'
```

### Run TEST Workflow
```bash
curl -X POST http://localhost:8881/api/v1/agent/claude-code/test/run \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer test-key" \
  -d '{
    "message": "Create comprehensive tests for the TODO API implementation",
    "session_id": "[SAME_SESSION_ID]",
    "max_turns": 40
  }'
```

## 🔍 Using HTTPie (cleaner syntax)

### Install HTTPie
```bash
pip install httpie
```

### List Workflows
```bash
http GET localhost:8881/api/v1/agent/claude-code/workflows \
  Authorization:"Bearer test-key"
```

### Run Workflow
```bash
http POST localhost:8881/api/v1/agent/claude-code/architect/run \
  Authorization:"Bearer test-key" \
  message="Design a TODO API" \
  max_turns=30
```

### Check Status
```bash
http GET localhost:8881/api/v1/agent/claude-code/run/[RUN_ID]/status \
  Authorization:"Bearer test-key"
```

## 📊 Expected Response Examples

### Workflow List Response
```json
[
  {
    "name": "architect",
    "description": "System design and technical decisions",
    "path": "/path/to/workflows/architect",
    "valid": true
  },
  {
    "name": "implement",
    "description": "Feature implementation and coding",
    "path": "/path/to/workflows/implement",
    "valid": true
  }
]
```

### Run Start Response
```json
{
  "run_id": "run_abc123def456",
  "status": "pending",
  "message": "Claude-Code architect workflow started",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "workflow_name": "architect",
  "started_at": "2025-01-06T10:30:00Z"
}
```

### Status Response (Running)
```json
{
  "run_id": "run_abc123def456",
  "status": "running",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "workflow_name": "architect",
  "started_at": "2025-01-06T10:30:00Z",
  "updated_at": "2025-01-06T10:32:00Z",
  "container_id": "claude-code-architect-xyz",
  "execution_time": 120.5
}
```

### Status Response (Completed)
```json
{
  "run_id": "run_abc123def456",
  "status": "completed",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "workflow_name": "architect",
  "started_at": "2025-01-06T10:30:00Z",
  "updated_at": "2025-01-06T10:35:00Z",
  "execution_time": 300.0,
  "result": "Successfully designed TODO API architecture",
  "exit_code": 0,
  "git_commits": ["abc123", "def456"],
  "error": null
}
```

## 🛠️ Troubleshooting

### Common Issues

1. **Authentication Error**
   - Ensure you're using the correct API key
   - Default test key: "test-key"

2. **Workflow Not Found**
   - Check available workflows first
   - Ensure workflow name is exact (case-sensitive)

3. **Claude CLI Not Configured**
   - Check health endpoint for status
   - Ensure `~/.claude/.credentials.json` exists

4. **Container Issues (Docker mode)**
   - Ensure Docker daemon is running
   - Check Docker permissions

5. **Session Not Found**
   - Verify session_id from previous run
   - Sessions expire after inactivity

### Debug Commands

```bash
# Check if server is running
curl http://localhost:8881/health

# Check Claude CLI credentials
ls -la ~/.claude/.credentials.json

# Check Docker (if using Docker mode)
docker ps | grep claude-code

# Check database for sessions
uv run python -c "from src.db.repository import session; print(len(session.list_sessions()))"
```

## 📝 Notes

- Default API port: 8881
- Default auth: Bearer token "test-key"
- Workflows run asynchronously - poll status endpoint
- Sessions maintain context between workflows
- Git commits are tracked per session
- Logs stream to `logs/server.log`