# OpenAPI Test Examples for Claude Code Workflows

## Overview

This document provides comprehensive test examples for all Claude Code workflow endpoints based on the OpenAPI specification. Each example includes request/response samples and expected behavior.

## API Base URL
```
http://localhost:28881/api/v1/workflows/claude-code
```

## Authentication
All endpoints require Bearer token authentication:
```bash
Authorization: Bearer {API_KEY}
```

---

## Endpoint: Execute Workflow

### POST `/run/{workflow_name}`

#### Basic Workflow Execution

**Request:**
```bash
curl -X POST \
  -H "Authorization: Bearer {API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Create a simple hello world function in Python",
    "max_turns": 5,
    "session_name": "basic-test"
  }' \
  "http://localhost:28881/api/v1/workflows/claude-code/run/builder"
```

**Response:**
```json
{
  "success": true,
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "session_id": "550e8400-e29b-41d4-a716-446655440001",
  "workflow_name": "builder",
  "status": "pending",
  "started_at": "2025-06-20T10:00:00Z",
  "message": "Workflow 'builder' started successfully",
  "tracking_info": {
    "run_id": "550e8400-e29b-41d4-a716-446655440000",
    "polling_command": "get_workflow_status('550e8400-e29b-41d4-a716-446655440000')",
    "expected_duration": "Variable (depends on complexity)",
    "max_turns": 5
  }
}
```

#### Workflow with External Repository

**Request:**
```bash
curl -X POST \
  -H "Authorization: Bearer {API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Analyze and fix any linting issues in the codebase",
    "repository_url": "https://github.com/user/test-repo.git",
    "git_branch": "main",
    "max_turns": 10,
    "session_name": "external-repo-fix",
    "create_pr_on_success": true,
    "pr_title": "fix: Resolve linting issues",
    "pr_body": "Automated fixes for code linting issues found during analysis."
  }' \
  "http://localhost:28881/api/v1/workflows/claude-code/run/surgeon?persistent=true"
```

#### Workflow with Session Continuation

**Request:**
```bash
curl -X POST \
  -H "Authorization: Bearer {API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Continue the previous implementation and add tests",
    "session_id": "550e8400-e29b-41d4-a716-446655440001",
    "max_turns": 15
  }' \
  "http://localhost:28881/api/v1/workflows/claude-code/run/guardian"
```

#### Workflow with All Parameters

**Request:**
```bash
curl -X POST \
  -H "Authorization: Bearer {API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Implement a comprehensive REST API with authentication, validation, and documentation",
    "max_turns": 20,
    "session_id": null,
    "session_name": "api-implementation",
    "user_id": "user-123",
    "git_branch": "feature/api-implementation",
    "repository_url": null,
    "timeout": 7200,
    "create_pr_on_success": true,
    "pr_title": "feat: Add comprehensive REST API",
    "pr_body": "## Summary\n- Implemented REST API with authentication\n- Added input validation\n- Generated comprehensive documentation\n\n## Test Plan\n- [x] Unit tests for all endpoints\n- [x] Integration tests\n- [x] API documentation verification"
  }' \
  "http://localhost:28881/api/v1/workflows/claude-code/run/builder?persistent=true"
```

---

## Endpoint: Get Workflow Status

### GET `/run/{run_id}/status`

#### Basic Status Check

**Request:**
```bash
curl -X GET \
  -H "Authorization: Bearer {API_KEY}" \
  "http://localhost:28881/api/v1/workflows/claude-code/run/550e8400-e29b-41d4-a716-446655440000/status"
```

**Response:**
```json
{
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "running",
  "workflow_name": "builder",
  "started_at": "2025-06-20T10:00:00Z",
  "completed_at": null,
  "execution_time_seconds": null,
  "progress": {
    "turns": 3,
    "max_turns": 5,
    "completion_percentage": 60.0,
    "current_phase": "implementation",
    "phases_completed": ["analysis", "planning"],
    "is_running": true,
    "estimated_completion": "2025-06-20T10:05:00Z"
  },
  "metrics": {
    "cost_usd": 0.0125,
    "tokens": {
      "total": 2500,
      "input": 1800,
      "output": 700,
      "cache_created": 500,
      "cache_read": 200,
      "cache_efficiency": 28.6
    },
    "tools_used": ["Read", "Write", "Bash"],
    "api_duration_ms": 15000,
    "performance_score": 85.0
  },
  "result": {
    "success": null,
    "completion_type": "running",
    "message": "🔄 Running - Turn 3, 3 tools used",
    "final_output": null,
    "files_created": ["hello.py"],
    "git_commits": []
  }
}
```

#### Detailed Status Check

**Request:**
```bash
curl -X GET \
  -H "Authorization: Bearer {API_KEY}" \
  "http://localhost:28881/api/v1/workflows/claude-code/run/550e8400-e29b-41d4-a716-446655440000/status?detailed=true&debug=true"
```

**Response:**
```json
{
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "workflow_name": "builder",
  "started_at": "2025-06-20T10:00:00Z",
  "completed_at": "2025-06-20T10:05:30Z",
  "execution_time_seconds": 330,
  "progress": {
    "turns": 5,
    "max_turns": 5,
    "completion_percentage": 100.0,
    "current_phase": "completed",
    "phases_completed": ["analysis", "planning", "implementation", "testing", "completion"],
    "is_running": false,
    "estimated_completion": null
  },
  "metrics": {
    "cost_usd": 0.0450,
    "tokens": {
      "total": 8500,
      "input": 6200,
      "output": 2300,
      "cache_created": 1500,
      "cache_read": 800,
      "cache_efficiency": 34.8
    },
    "tools_used": ["Read", "Write", "Bash", "Edit", "MultiEdit"],
    "api_duration_ms": 45000,
    "performance_score": 92.0
  },
  "result": {
    "success": true,
    "completion_type": "completed_successfully",
    "message": "✅ Workflow completed successfully",
    "final_output": "Successfully created hello.py with comprehensive documentation and tests.",
    "files_created": ["hello.py", "test_hello.py", "README.md"],
    "git_commits": ["feat: Add hello world function with tests"]
  },
  "debug": {
    "session_info": {
      "session_id": "550e8400-e29b-41d4-a716-446655440001",
      "claude_session_id": "claude-session-xyz",
      "container_id": null,
      "run_id": "550e8400-e29b-41d4-a716-446655440000",
      "workflow_name": "builder",
      "started_at": "2025-06-20T10:00:00Z",
      "git_branch": null,
      "repository_url": null
    },
    "execution_details": {
      "exit_code": 0,
      "max_turns": 5,
      "current_turns": 5,
      "timeout_seconds": 3600,
      "execution_time": 330,
      "run_status": "completed",
      "git_commits": ["abc123: feat: Add hello world function"],
      "container_status": null
    },
    "tool_usage": {
      "total_tool_calls": 8,
      "unique_tools_used": 5,
      "tool_breakdown": {
        "Read": 2,
        "Write": 3,
        "Bash": 1,
        "Edit": 1,
        "MultiEdit": 1
      },
      "most_used_tool": "Write"
    },
    "timing_analysis": {
      "started_at": "2025-06-20T10:00:00Z",
      "execution_time_seconds": 330,
      "current_turns": 5,
      "average_turn_time_seconds": 66,
      "estimated_total_duration": null,
      "last_activity": "2025-06-20T10:05:30Z"
    },
    "cost_breakdown": {
      "total_cost_usd": 0.045,
      "input_tokens": 6200,
      "output_tokens": 2300,
      "cache_creation_tokens": 1500,
      "cache_read_tokens": 800,
      "total_tokens": 8500,
      "cost_per_token": 0.0000053,
      "cache_efficiency_percent": 34.8
    },
    "workflow_phases": {
      "phases_detected": ["analysis", "planning", "implementation", "testing", "completion"],
      "current_phase": "completed",
      "phase_breakdown": [
        {"phase": "analysis", "duration": 45, "turns": 1},
        {"phase": "planning", "duration": 30, "turns": 1},
        {"phase": "implementation", "duration": 180, "turns": 2},
        {"phase": "testing", "duration": 60, "turns": 1},
        {"phase": "completion", "duration": 15, "turns": 0}
      ],
      "total_phases": 5
    },
    "performance_metrics": {
      "turn_efficiency_percent": 92,
      "time_per_turn_seconds": 66,
      "estimated_completion_percent": 100,
      "resource_utilization": {
        "memory_usage": "normal",
        "cpu_usage": "low",
        "disk_usage": "low",
        "network_usage": "minimal"
      }
    },
    "error_analysis": {
      "total_errors": 0,
      "error_rate_percent": 0,
      "recent_errors": [],
      "error_patterns": []
    },
    "raw_stream_sample": [
      "Starting implementation...",
      "Creating hello.py file...",
      "Adding tests...",
      "Workflow completed successfully."
    ]
  }
}
```

---

## Endpoint: List Workflow Runs

### GET `/runs`

#### List All Runs

**Request:**
```bash
curl -X GET \
  -H "Authorization: Bearer {API_KEY}" \
  "http://localhost:28881/api/v1/workflows/claude-code/runs"
```

#### List Runs with Filters

**Request:**
```bash
curl -X GET \
  -H "Authorization: Bearer {API_KEY}" \
  "http://localhost:28881/api/v1/workflows/claude-code/runs?status=completed&workflow_name=builder&limit=10&offset=0"
```

**Response:**
```json
{
  "runs": [
    {
      "run_id": "550e8400-e29b-41d4-a716-446655440000",
      "workflow_name": "builder",
      "status": "completed",
      "started_at": "2025-06-20T10:00:00Z",
      "completed_at": "2025-06-20T10:05:30Z",
      "execution_time_seconds": 330,
      "cost_usd": 0.045,
      "success": true,
      "user_id": "user-123",
      "session_name": "basic-test"
    }
  ],
  "pagination": {
    "total": 1,
    "limit": 10,
    "offset": 0,
    "has_more": false
  }
}
```

---

## Endpoint: Kill Workflow

### POST `/run/{run_id}/kill`

**Request:**
```bash
curl -X POST \
  -H "Authorization: Bearer {API_KEY}" \
  "http://localhost:28881/api/v1/workflows/claude-code/run/550e8400-e29b-41d4-a716-446655440000/kill"
```

**Response:**
```json
{
  "success": true,
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Workflow killed successfully",
  "status": "cancelled",
  "killed_at": "2025-06-20T10:03:00Z"
}
```

---

## Endpoint: List Available Workflows

### GET `/workflows`

**Request:**
```bash
curl -X GET \
  -H "Authorization: Bearer {API_KEY}" \
  "http://localhost:28881/api/v1/workflows/claude-code/workflows"
```

**Response:**
```json
{
  "workflows": [
    {
      "name": "guardian",
      "description": "🛡️ GUARDIAN - Protector Workflow",
      "valid": true,
      "capabilities": ["testing", "validation", "security_audit"]
    },
    {
      "name": "surgeon",
      "description": "⚕️ SURGEON - Precision Code Healer Workflow",
      "valid": true,
      "capabilities": ["bug_fixing", "code_refactoring", "surgical_edits"]
    },
    {
      "name": "brain",
      "description": "🧠 BRAIN – Collective Memory & Intelligence Orchestrator",
      "valid": true,
      "capabilities": ["knowledge_management", "pattern_storage", "analysis"]
    },
    {
      "name": "genie",
      "description": "🧞 GENIE - Automagik Agents Platform Orchestration Consciousness",
      "valid": true,
      "capabilities": ["workflow_orchestration", "task_coordination", "planning"]
    },
    {
      "name": "shipper",
      "description": "📦 SHIPPER - Platform Production Deployment Orchestrator Workflow",
      "valid": true,
      "capabilities": ["deployment", "release_management", "ci_cd"]
    },
    {
      "name": "lina",
      "description": "👩‍💼 LINA - Linear Integration Orchestrator Workflow",
      "valid": true,
      "capabilities": ["project_management", "linear_integration", "issue_tracking"]
    },
    {
      "name": "builder",
      "description": "🔨 BUILDER - Creator Workflow",
      "valid": true,
      "capabilities": ["implementation", "feature_development", "code_creation"]
    }
  ]
}
```

---

## Endpoint: Health Check

### GET `/health`

**Request:**
```bash
curl -X GET \
  -H "Authorization: Bearer {API_KEY}" \
  "http://localhost:28881/api/v1/workflows/claude-code/health"
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-06-20T10:00:00Z",
  "version": "1.0.0",
  "workflows_available": 7,
  "active_runs": 2,
  "system_resources": {
    "memory_usage": "normal",
    "cpu_usage": "low",
    "disk_usage": "low"
  }
}
```

---

## Error Response Examples

### 400 Bad Request
```json
{
  "success": false,
  "error": "Validation error",
  "detail": [
    {
      "loc": ["message"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ],
  "timestamp": "2025-06-20T10:00:00Z"
}
```

### 401 Unauthorized
```json
{
  "success": false,
  "error": "Invalid API key",
  "detail": "Authentication required",
  "timestamp": "2025-06-20T10:00:00Z"
}
```

### 404 Not Found
```json
{
  "success": false,
  "error": "Workflow not found",
  "detail": "Workflow 'invalid-workflow' not found. Available: [guardian, surgeon, brain, genie, shipper, lina, builder]",
  "timestamp": "2025-06-20T10:00:00Z"
}
```

### 422 Validation Error
```json
{
  "success": false,
  "error": "Validation error",
  "detail": [
    {
      "loc": ["max_turns"],
      "msg": "ensure this value is less than or equal to 200",
      "type": "value_error.number.not_le",
      "ctx": {"limit_value": 200}
    }
  ],
  "timestamp": "2025-06-20T10:00:00Z"
}
```

### 500 Internal Server Error
```json
{
  "success": false,
  "error": "Internal server error",
  "detail": "An unexpected error occurred",
  "timestamp": "2025-06-20T10:00:00Z"
}
```

---

## Testing Guidelines

### Test Data Requirements

1. **Valid API Key**: Required for all requests
2. **Test Repositories**: For repository_url testing
3. **Git Branches**: Existing branches for git_branch testing
4. **Session IDs**: Valid UUIDs for session continuation
5. **Linear Configuration**: For lina workflow testing

### Parameter Validation Testing

1. **Required Fields**: Test with missing required fields
2. **Type Validation**: Test with wrong data types
3. **Range Validation**: Test boundary conditions (max_turns, timeout)
4. **Format Validation**: Test UUID format for session_id
5. **URL Validation**: Test repository_url format

### Workflow-Specific Testing

1. **Guardian**: Focus on testing and validation tasks
2. **Surgeon**: Test bug fixing and refactoring scenarios
3. **Brain**: Test knowledge storage and retrieval
4. **Genie**: Test workflow orchestration capabilities
5. **Shipper**: Test deployment and release workflows
6. **Lina**: Test Linear integration features
7. **Builder**: Test implementation and creation tasks

### Performance Testing

1. **Concurrent Requests**: Multiple simultaneous workflows
2. **Large Inputs**: Test with long messages and complex tasks
3. **Long-Running Workflows**: Test timeout behavior
4. **Resource Limits**: Test system resource constraints

This comprehensive documentation ensures complete coverage of all API endpoints and parameter combinations for thorough testing of the Claude Code workflow system.