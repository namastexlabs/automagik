# Claude Code API Payload Documentation

## 1. Run Workflow Endpoint

**Endpoint:** `POST /api/v1/agent/claude-code/run`

### Full Payload with All Fields

```json
{
  "workflow_name": "test",
  "message": "Hello! Please list your top 3 most useful tools and briefly explain what each one does.",
  "max_turns": 1,
  "repository_url": "https://github.com/namastexlabs/am-agents-labs.git",
  "git_branch": "feature/new-agent-implementation",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "timeout": 3600,
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "session_name": "claude-test-tools-demo"
}
```

### Field Documentation

| Field | Type | Required | Default | Description | Example Values |
|-------|------|----------|---------|-------------|----------------|
| **workflow_name** | string | ✅ Yes | - | The workflow to execute | `"test"`, `"architect"`, `"implement"`, `"fix"`, `"refactor"`, `"review"`, `"document"`, `"pr"` |
| **message** | string | ✅ Yes | - | Task description for Claude to execute | `"Fix the authentication bug in user controller"`, `"List your available tools"`, `"Review the latest PR changes"` |
| **max_turns** | integer | ❌ No | 30 | Maximum conversation turns (1-100) | `1` (quick task), `10` (simple task), `50` (complex task), `100` (very complex) |
| **repository_url** | string | ❌ No | Current repo | Git repository URL to clone | `"https://github.com/anthropics/claude-cli.git"`, `"git@github.com:user/repo.git"` |
| **git_branch** | string | ❌ No | Current branch | Git branch to work on (defaults to current branch) | `"main"`, `"develop"`, `"feature/new-api"`, `"fix/bug-123"` |
| **session_id** | string | ❌ No | null | Session ID for continuation | `"550e8400-e29b-41d4-a716-446655440000"` (UUID format) |
| **timeout** | integer | ❌ No | 7200 | Execution timeout in seconds (60-14400) | `3600` (1 hour), `7200` (2 hours), `14400` (4 hours max) |
| **user_id** | string | ❌ No | null | User ID for the request | `"123e4567-e89b-12d3-a456-426614174000"` (UUID format) |
| **session_name** | string | ❌ No | Auto-generated | Custom session name | `"bug-fix-auth"`, `"feature-api-v2"`, `"test-integration"` |

### Example Payloads by Use Case

#### 1. Quick Tool Listing (Minimal)
```json
{
  "workflow_name": "test",
  "message": "List your top 3 tools with brief descriptions",
  "max_turns": 1
}
```

#### 2. Bug Fix with Custom Branch
```json
{
  "workflow_name": "fix",
  "message": "Fix the session timeout issue in the authentication middleware. Users are getting logged out after 5 minutes instead of 30 minutes.",
  "max_turns": 50,
  "git_branch": "fix/session-timeout-bug",
  "session_name": "fix-auth-timeout"
}
```

#### 3. Feature Implementation with External Repo
```json
{
  "workflow_name": "implement",
  "message": "Implement a new REST API endpoint for user profile updates with validation",
  "max_turns": 75,
  "repository_url": "https://github.com/mycompany/backend-api.git",
  "git_branch": "feature/user-profile-api",
  "timeout": 10800,
  "session_name": "implement-user-profile-api"
}
```

#### 4. Code Review Task
```json
{
  "workflow_name": "review",
  "message": "Review the changes in the latest pull request for security vulnerabilities and code quality",
  "max_turns": 30,
  "git_branch": "pr/feature-payment-integration",
  "user_id": "reviewer-123e4567-e89b-12d3-a456-426614174000"
}
```

#### 5. Architecture Design
```json
{
  "workflow_name": "architect", 
  "message": "Design a scalable microservices architecture for an e-commerce platform with user service, product service, and order service",
  "max_turns": 40,
  "timeout": 7200,
  "session_name": "architect-ecommerce-microservices"
}
```

#### 6. Continue Previous Session
```json
{
  "workflow_name": "implement",
  "message": "Continue implementing the remaining unit tests for the user service",
  "session_id": "8a5b3c12-4def-6789-0abc-123456789def",
  "max_turns": 30
}
```

## 2. Get Status Endpoint

**Endpoint:** `GET /api/v1/run/{run_id}/status`

### Request
```bash
curl -X GET "http://localhost:28881/api/v1/run/run_d79db57da038/status" \
  -H "x-api-key: namastex888"
```

### Response Example
```json
{
  "run_id": "run_d79db57da038",
  "status": "completed",
  "session_id": "8ec95087-6364-44db-9354-4acde6d96e8d",
  "workflow_name": "test",
  "started_at": "2025-01-10T12:30:45.123456",
  "updated_at": "2025-01-10T12:31:23.456789",
  "container_id": "a1b2c3d4e5f6",
  "execution_time": 38.33,
  "result": "Here are my top 3 most useful tools:\n\n1. **Task** - Launches new agents for complex searches...",
  "exit_code": 0,
  "git_commits": ["abc123def456", "789ghi012jkl"],
  "error": null,
  "logs": "2025-01-10T12:30:45.123456 [init] Starting Claude Code execution...\n2025-01-10T12:30:46.234567 [session_confirmed] Claude session started: 41e16bbc-fa74-414e-bd1e-424a9b4aeddd\n..."
}
```

### Status Values
- `pending` - Run is queued but not started
- `running` - Currently executing in container
- `completed` - Finished successfully
- `failed` - Failed with an error

## 3. List Workflows Endpoint

**Endpoint:** `GET /api/v1/agent/claude-code/workflows`

### Request
```bash
curl -X GET "http://localhost:28881/api/v1/agent/claude-code/workflows" \
  -H "x-api-key: namastex888"
```

### Response Example
```json
[
  {
    "name": "architect",
    "description": "Design system architecture and technical specifications",
    "path": "/src/agents/claude_code/workflows/architect",
    "valid": true
  },
  {
    "name": "test",
    "description": "Create comprehensive tests and validate system quality",
    "path": "/src/agents/claude_code/workflows/test", 
    "valid": true
  },
  {
    "name": "fix",
    "description": "Fix bugs and issues in code with minimal changes",
    "path": "/src/agents/claude_code/workflows/fix",
    "valid": true
  }
]
```

## 4. Health Check Endpoint

**Endpoint:** `GET /api/v1/agent/claude-code/health`

### Request
```bash
curl -X GET "http://localhost:28881/api/v1/agent/claude-code/health" \
  -H "x-api-key: namastex888"
```

### Response Example
```json
{
  "status": "healthy",
  "timestamp": "2025-01-10T12:35:00.123456",
  "agent_available": true,
  "workflows": {
    "architect": true,
    "implement": true,
    "test": true,
    "review": true,
    "fix": true,
    "refactor": true,
    "document": true,
    "pr": true
  },
  "container_manager": true,
  "feature_enabled": true,
  "claude_cli_path": "/home/user/.nvm/versions/node/v22.16.0/bin/claude"
}
```

## Authentication

All endpoints require the `x-api-key` header:

```bash
-H "x-api-key: namastex888"
```

## Common cURL Examples

### 1. Run a Simple Test
```bash
curl -X POST "http://localhost:28881/api/v1/agent/claude-code/run" \
  -H "x-api-key: namastex888" \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_name": "test",
    "message": "List your top 3 tools",
    "max_turns": 1
  }'
```

### 2. Fix a Bug with Custom Branch
```bash
curl -X POST "http://localhost:28881/api/v1/agent/claude-code/run" \
  -H "x-api-key: namastex888" \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_name": "fix",
    "message": "Fix the null pointer exception in user service",
    "max_turns": 50,
    "git_branch": "fix/null-pointer-user-service",
    "session_name": "bug-fix-npe"
  }'
```

### 3. Work on External Repository
```bash
curl -X POST "http://localhost:28881/api/v1/agent/claude-code/run" \
  -H "x-api-key: namastex888" \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_name": "implement",
    "message": "Add unit tests for the payment service",
    "repository_url": "https://github.com/myorg/payment-service.git",
    "git_branch": "feature/add-unit-tests",
    "max_turns": 60,
    "timeout": 5400
  }'
```