# Workflow API Structure Analysis

## Overview
This document provides a comprehensive analysis of the existing workflow endpoints structure, API patterns, and recommendations for creating a compatibility layer.

## 1. Existing Workflow Endpoints

### Main Claude Code Router
- **Base Path**: `/api/v1/workflows/claude-code`
- **Location**: `src/api/routes/claude_code_routes.py`

### Current Endpoints

#### 1.1 Execute Workflow
```python
POST /workflows/claude-code/run/{workflow_name}
```
- **Request Model**: `ClaudeWorkflowRequest`
  - `message`: Main task description
  - `max_turns`: Maximum conversation turns (1-100)
  - `session_id`: Optional session continuation
  - `session_name`: Human-readable session name
  - `user_id`: User identifier
  - `git_branch`: Git branch to work on
  - `repository_url`: External repository URL
  - `timeout`: Execution timeout (60-14400 seconds)

- **Response Model**: `ClaudeWorkflowResponse`
  - `run_id`: Unique run identifier
  - `status`: pending, running, completed, failed
  - `message`: Human-readable status message
  - `session_id`: Session identifier
  - `workflow_name`: Executed workflow name
  - `started_at`: ISO timestamp

#### 1.2 List Runs
```python
GET /workflows/claude-code/runs
```
- **Query Parameters**:
  - `page`, `page_size`: Pagination
  - `status`, `workflow_name`, `user_id`: Filters
  - `sort_by`, `sort_order`: Sorting options

- **Response Model**: `ClaudeCodeRunsListResponse`
  - List of `ClaudeCodeRunSummary` objects
  - Includes execution metrics, tokens, costs

#### 1.3 Get Run Status
```python
GET /workflows/claude-code/run/{run_id}/status
```
- **Query Parameters**: `debug` (optional)
- **Response Models**: 
  - `EnhancedStatusResponse` (normal)
  - `DebugStatusResponse` (with debug=true)

#### 1.4 List Workflows
```python
GET /workflows/claude-code/workflows
```
- **Response**: List of `WorkflowInfo` objects

#### 1.5 Kill Run
```python
POST /workflows/claude-code/run/{run_id}/kill
```
- **Query Parameters**: `force` (optional)
- **Response**: Kill confirmation with cleanup status

#### 1.6 Health Check
```python
GET /workflows/claude-code/health
```

#### 1.7 Monitoring Endpoints (GUARDIAN)
- `GET /workflows/claude-code/monitoring/status`
- `GET /workflows/claude-code/monitoring/health`
- `POST /workflows/claude-code/monitoring/start`
- `POST /workflows/claude-code/monitoring/stop`
- `POST /workflows/claude-code/monitoring/register`
- `POST /workflows/claude-code/monitoring/heartbeat`

## 2. WorkflowProcess Model Structure

### Database Schema
```sql
CREATE TABLE workflow_processes (
    run_id TEXT PRIMARY KEY,
    pid INTEGER,
    status TEXT NOT NULL DEFAULT 'running',
    workflow_name TEXT,
    session_id TEXT,
    user_id TEXT,
    started_at TIMESTAMP,
    workspace_path TEXT,
    last_heartbeat TIMESTAMP,
    process_info TEXT DEFAULT '{}',
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

### Pydantic Model
```python
class WorkflowProcess(BaseDBModel):
    run_id: str                          # Unique identifier
    pid: Optional[int]                   # System process ID
    status: str                          # running, completed, failed, killed
    workflow_name: Optional[str]         # Workflow name
    session_id: Optional[str]            # Associated session ID
    user_id: Optional[str]               # User who initiated
    workspace_path: Optional[str]        # Workspace directory
    process_info: Dict[str, Any]         # Additional metadata
    started_at: Optional[datetime]
    last_heartbeat: Optional[datetime]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
```

## 3. Response Format Patterns

### Standard Response Structure
```python
{
    "status": "success|error",
    "data": {},                    # Main response data
    "message": "Human-readable message",
    "timestamp": "ISO timestamp"
}
```

### Workflow Execution Response
```python
{
    "run_id": "uuid",
    "status": "pending|running|completed|failed",
    "workflow_name": "workflow_name",
    "session_id": "session_uuid",
    "started_at": "ISO timestamp",
    "completed_at": "ISO timestamp",
    "execution_time_seconds": 123.45,
    "metrics": {
        "cost_usd": 0.05,
        "tokens": {...},
        "tools_used": ["Read", "Edit"],
        "api_duration_ms": 12345
    },
    "result": {
        "success": true,
        "message": "Completion message",
        "files_created": ["file1.py"],
        "git_commits": []
    }
}
```

## 4. JSONL File Creation Mechanism

### Location Pattern
```
./logs/run_{run_id}_stream.jsonl
```

### Creation Process
1. **Initialization**: Created when CLI executor starts
2. **Content**: Each line is a JSON object with:
   - Original event data
   - `_timestamp` field added
   - All Claude CLI stream events

### File Structure
```jsonl
{"type":"system","subtype":"init","session_id":"...", "_timestamp":"2025-06-17T..."}
{"type":"assistant","message":{...}, "_timestamp":"2025-06-17T..."}
{"type":"tool_use","name":"Read",..., "_timestamp":"2025-06-17T..."}
{"type":"result","cost_usd":0.05,..., "_timestamp":"2025-06-17T..."}
```

### Usage
- Immutable audit trail of execution
- Parsed by `StreamParser` for status/metrics
- Source of truth for run reconstruction

## 5. Current API Structure

### Request Flow
1. Client → API Endpoint
2. Validate workflow exists
3. Create/Get user and session
4. Start async execution
5. Return immediately with run_id
6. Background task executes workflow

### Session Management
- Sessions stored in database
- Metadata includes run status, metrics
- Can continue existing sessions
- Session name support for easy lookup

### Status Tracking
- Real-time via session metadata
- Historical via JSONL parsing
- Metrics aggregation from multiple sources

## 6. Recommendations for Compatibility Layer

### 6.1 URL Structure Mapping
```
/v1/workflows/{workflow_name}/run → POST /workflows/claude-code/run/{workflow_name}
/v1/workflows/runs               → GET /workflows/claude-code/runs
/v1/workflows/runs/{run_id}      → GET /workflows/claude-code/run/{run_id}/status
```

### 6.2 Request/Response Translation
Create adapter classes:
```python
class WorkflowCompatibilityAdapter:
    def translate_request(self, v1_request) -> ClaudeWorkflowRequest
    def translate_response(self, internal_response) -> V1Response
    def translate_status(self, enhanced_status) -> V1Status
```

### 6.3 Backward Compatibility Considerations
1. **Field Mapping**: Map old field names to new ones
2. **Status Values**: Ensure consistent status strings
3. **Error Handling**: Maintain error response format
4. **Optional Fields**: Handle missing fields gracefully

### 6.4 Implementation Approach
1. Create new router with v1 paths
2. Use existing claude_code_router handlers
3. Add translation layer for requests/responses
4. Maintain same authentication/authorization
5. Log compatibility endpoint usage

### 6.5 Testing Strategy
1. Create test suite comparing v1 and current endpoints
2. Validate response format compatibility
3. Test session continuation
4. Verify metric accuracy
5. Load test both endpoint sets

## 7. Available Workflows

Based on directory structure:
- `brain` - Complex reasoning and analysis
- `builder` - Code implementation
- `genie` - General purpose assistant
- `guardian` - Safety and monitoring
- `lina` - Linear integration
- `shipper` - Deployment and shipping
- `surgeon` - Surgical code fixes

Each workflow has:
- `prompt.md` - System prompt
- `allowed_tools.json` - Tool restrictions

## 8. Key Integration Points

### 8.1 Database Tables
- `sessions` - Stores session metadata
- `workflow_processes` - Tracks active processes
- `messages` - Conversation history
- `users` - User information

### 8.2 Log Management
- `LogManager` - Centralized logging
- JSONL files for audit trail
- Real-time streaming support

### 8.3 Process Management
- `ClaudeCLIExecutor` - Manages CLI processes
- `WorkflowMonitor` - GUARDIAN monitoring
- Emergency kill functionality

## Conclusion

The existing workflow API is well-structured with comprehensive features including:
- Async execution with immediate response
- Session continuation support
- Real-time status tracking
- Detailed metrics and cost tracking
- JSONL audit trail
- Emergency termination
- GUARDIAN monitoring system

A compatibility layer can be implemented by:
1. Creating adapter routes that map to existing handlers
2. Translating request/response formats
3. Maintaining consistent status values
4. Preserving all existing functionality

The JSONL files provide a robust audit trail and can be leveraged for historical analysis and debugging.