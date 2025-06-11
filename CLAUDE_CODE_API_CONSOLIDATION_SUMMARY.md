# Claude Code API Consolidation Summary

## Changes Made

### 1. **Moved workflow_name from URL to Request Body**
- **Before**: `POST /api/v1/agent/claude-code/{workflow_name}/run`
- **After**: `POST /api/v1/agent/claude-code/run`
- The `workflow_name` is now a required field in the request body

### 2. **Added Logs to Status Endpoint**
- The `/run/{run_id}/status` endpoint now includes logs in the response
- Returns the last 1000 log entries to avoid overly large responses
- Log entries are formatted as text with timestamp, event type, and message

### 3. **Removed Redundant Endpoints**
The following endpoints have been removed:
- `GET /api/v1/agent/claude-code/run/{run_id}/logs`
- `GET /api/v1/agent/claude-code/run/{run_id}/logs/summary`
- `GET /api/v1/agent/claude-code/logs`

## Final API Structure

### Endpoints Kept:
1. **POST /api/v1/agent/claude-code/run**
   - Request body includes `workflow_name` field
   - Starts a Claude Code workflow execution
   - Returns run_id for status tracking

2. **GET /api/v1/agent/claude-code/run/{run_id}/status**
   - Returns complete run status
   - Now includes logs (last 1000 entries) in the response
   - No need for separate log endpoints

3. **GET /api/v1/agent/claude-code/workflows**
   - Lists available workflows
   - No changes made

4. **GET /api/v1/agent/claude-code/health**
   - Health check endpoint
   - No changes made

## Request/Response Examples

### Run Endpoint (Updated)
```bash
POST /api/v1/agent/claude-code/run
{
    "workflow_name": "fix",  # Now in request body
    "message": "Fix the session timeout issue",
    "git_branch": "fix/session-timeout",
    "max_turns": 50,
    "repository_url": "https://github.com/myorg/myrepo.git"
}
```

### Status Endpoint (Enhanced)
```json
{
    "run_id": "run_abc123",
    "status": "running",
    "session_id": "...",
    "workflow_name": "fix",
    "started_at": "2024-01-10T10:00:00",
    "updated_at": "2024-01-10T10:05:00",
    "container_id": "docker_container_id",
    "execution_time": 300.5,
    "result": null,
    "exit_code": null,
    "git_commits": [],
    "error": null,
    "logs": "2024-01-10T10:00:00 [start] Starting workflow...\n2024-01-10T10:00:01 [log] Analyzing code..."
}
```

## Testing

Run the test script to verify the changes:
```bash
uv run python test_claude_code_api_consolidated.py
```

## Benefits

1. **Simpler API**: Fewer endpoints to maintain and document
2. **Consistent Design**: All workflow configuration in request body
3. **One-Stop Status**: Get everything about a run (including logs) in one call
4. **Reduced Complexity**: No need to make multiple API calls for full run information