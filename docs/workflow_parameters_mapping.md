# Claude Code Workflow Parameters and Use Cases Mapping

## Workflow Parameters

### 1. **message** (required)
- **Type**: `str`
- **Description**: The task message for Claude to execute
- **Validation**: Cannot be empty
- **Use Cases**:
  - Simple task: "Create a hello world script"
  - Complex task: "Implement user authentication with JWT tokens"
  - Bug fix: "Fix the session timeout issue in agent controller"
  - Research: "Analyze the current codebase structure and suggest improvements"

### 2. **workflow_name** (required)
- **Type**: `str`
- **Default**: `"surgeon"`
- **Available Workflows**:
  - `genie` - Orchestrator consciousness that coordinates other workflows
  - `builder` - Implementation and feature development
  - `guardian` - Testing, validation, and quality assurance
  - `surgeon` - Bug fixing and issue resolution
  - `shipper` - Deployment and release preparation
  - `lina` - Linear integration and project management
  - `brain` - Knowledge management and pattern storage
  - `flashinho_thinker` - Deep thinking and analysis
- **Use Cases**:
  - Use `builder` for new features
  - Use `surgeon` for bug fixes
  - Use `guardian` for test creation
  - Use `brain` for knowledge extraction

### 3. **session_id** (optional)
- **Type**: `Optional[str]`
- **Description**: Continue a previous Claude session
- **Use Cases**:
  - Resume interrupted work
  - Continue complex multi-step tasks
  - Maintain context across multiple requests

### 4. **run_id** (optional)
- **Type**: `Optional[str]`
- **Description**: Unique identifier for tracking and persistence
- **Use Cases**:
  - Database tracking
  - Progress monitoring
  - Result retrieval
  - Kill/cancel operations

### 5. **max_turns** (optional)
- **Type**: `Optional[int]`
- **Range**: 1-200
- **Default**: None (unlimited)
- **Use Cases**:
  - Limit execution for simple tasks (5-10 turns)
  - Medium complexity (20-50 turns)
  - Complex implementations (50-100 turns)
  - Research/exploration (100-200 turns)

### 6. **model** (optional)
- **Type**: `Optional[str]`
- **Default**: `"sonnet"`
- **Options**: Various Claude models
- **Use Cases**:
  - Use default for most tasks
  - Use more powerful models for complex reasoning
  - Use faster models for simple tasks

### 7. **max_thinking_tokens** (optional)
- **Type**: `Optional[int]`
- **Description**: Maximum tokens for reasoning
- **Use Cases**:
  - Complex problem solving
  - Architecture design
  - Deep analysis tasks

### 8. **timeout** (optional)
- **Type**: `Optional[int]`
- **Range**: 60-7200 seconds (1 minute to 2 hours)
- **Default**: 3600 (1 hour)
- **Use Cases**:
  - Quick fixes: 300-600 seconds
  - Standard tasks: 1800-3600 seconds
  - Complex implementations: 5400-7200 seconds

### 9. **git_branch** (optional)
- **Type**: `Optional[str]`
- **Description**: Git branch to work on
- **Use Cases**:
  - Feature branches: `feature/user-auth`
  - Bug fix branches: `fix/session-timeout`
  - Experiment branches: `experiment/new-architecture`

### 10. **repository_url** (optional)
- **Type**: `Optional[str]`
- **Description**: External repository to clone
- **Use Cases**:
  - Work on external projects
  - Clone and analyze repositories
  - Cross-repository operations

### 11. **persistent** (optional)
- **Type**: `bool`
- **Default**: `True`
- **Description**: Keep workspace after completion
- **Use Cases**:
  - `True`: Keep for manual review, debugging, or continuation
  - `False`: Clean up after automated tasks

### 12. **auto_merge** (optional)
- **Type**: `bool`
- **Default**: `False`
- **Description**: Automatically merge to main branch
- **Use Cases**:
  - `True`: Automated deployments, trusted fixes
  - `False`: Manual review required

### 13. **temp_workspace** (optional)
- **Type**: `bool`
- **Default**: `False`
- **Description**: Use isolated temporary workspace
- **Incompatible with**: `repository_url`, `git_branch`, `auto_merge`
- **Use Cases**:
  - Experiments without affecting main codebase
  - Testing in isolation
  - Proof of concepts

### 14. **environment** (optional)
- **Type**: `Optional[Dict[str, str]]`
- **Description**: Additional environment variables
- **Use Cases**:
  - Custom API keys
  - Configuration overrides
  - Tool-specific settings

## Common Use Case Scenarios

### 1. **Simple Bug Fix**
```json
{
  "message": "Fix the null pointer exception in user service",
  "workflow_name": "surgeon",
  "max_turns": 20,
  "git_branch": "fix/null-pointer",
  "timeout": 1800
}
```

### 2. **Feature Implementation**
```json
{
  "message": "Implement user authentication with JWT tokens",
  "workflow_name": "builder",
  "max_turns": 50,
  "git_branch": "feature/jwt-auth",
  "timeout": 3600,
  "persistent": true
}
```

### 3. **Test Creation**
```json
{
  "message": "Create comprehensive unit tests for the payment service",
  "workflow_name": "guardian",
  "max_turns": 30,
  "git_branch": "test/payment-service"
}
```

### 4. **Knowledge Extraction**
```json
{
  "message": "Analyze the codebase and document all API endpoints",
  "workflow_name": "brain",
  "max_turns": 100,
  "persistent": true
}
```

### 5. **Temporary Experiment**
```json
{
  "message": "Experiment with a new architecture pattern",
  "workflow_name": "builder",
  "temp_workspace": true,
  "max_turns": 40,
  "persistent": false
}
```

### 6. **External Repository Analysis**
```json
{
  "message": "Analyze and document the architecture of this project",
  "workflow_name": "brain",
  "repository_url": "https://github.com/org/project.git",
  "max_turns": 80,
  "timeout": 5400
}
```

### 7. **Automated Deployment**
```json
{
  "message": "Prepare release v1.2.0 with changelog",
  "workflow_name": "shipper",
  "auto_merge": true,
  "max_turns": 30
}
```

### 8. **Session Continuation**
```json
{
  "message": "Continue implementing the remaining API endpoints",
  "session_id": "previous-session-id",
  "workflow_name": "builder",
  "max_turns": 50
}
```

## Possible Execution Outcomes

### 1. **Successful Completion**
- Status: `completed`
- All tasks finished within turn/time limits
- Result available in workspace
- Session can be continued if needed

### 2. **Turn Limit Reached**
- Status: `completed` (with metadata indicating limit reached)
- Work partially done
- Can continue with session_id
- Review what was accomplished

### 3. **Timeout**
- Status: `failed` or `completed` (depends on graceful shutdown)
- Time limit exceeded
- Partial work may be available
- Can continue with session_id

### 4. **Killed/Cancelled**
- Status: `killed`
- User manually stopped execution
- Partial work preserved if persistent=true
- Can continue from stopping point

### 5. **Error/Failure**
- Status: `failed`
- Execution error occurred
- Error details in logs
- May need debugging or different approach

### 6. **PM2 Environment Issues**
- Workflow starts but hangs
- No token/turn progress
- Related to asyncio subprocess issues
- Requires environment adjustment

## Validation Points

1. **Pre-execution Validation**:
   - Workflow exists in filesystem
   - Parameters are compatible
   - Workspace is accessible
   - Claude CLI is available

2. **During Execution**:
   - Progress tracking (turns, tokens)
   - Message processing
   - Tool execution
   - Error handling

3. **Post-execution Validation**:
   - Final status update
   - Result compilation
   - Workspace state
   - Database updates

## Testing Strategy

1. **Unit Tests**: Test each parameter validation
2. **Integration Tests**: Test parameter combinations
3. **Workflow Tests**: Test each workflow type
4. **Edge Cases**: Test limits and error conditions
5. **Environment Tests**: Test under different environments (PM2, direct, etc.)