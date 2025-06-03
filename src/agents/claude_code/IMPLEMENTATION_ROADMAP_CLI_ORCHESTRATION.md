# Claude CLI Orchestration Implementation Roadmap

## Overview

This roadmap details the implementation of CLI-based Claude Code workflow execution with Genie orchestration integration.

## Week 1: Core Infrastructure

### Day 1-2: Environment Manager
```python
# src/agents/claude_code/cli_environment.py
class CLIEnvironmentManager:
    """Manages isolated CLI execution environments"""
    
    async def create_workspace(run_id: str) -> Path:
        """Create isolated workspace in /tmp"""
        
    async def setup_repository(workspace: Path, branch: str):
        """Clone and checkout branch"""
        
    async def copy_configs(workspace: Path):
        """Copy .env, .mcp.json, allowed_tools.json"""
        
    async def cleanup(workspace: Path):
        """Remove workspace and all contents"""
```

**Tasks**:
- [ ] Implement workspace creation with proper permissions
- [ ] Add repository cloning with branch support
- [ ] Create config file management
- [ ] Implement cleanup with retry logic
- [ ] Add comprehensive error handling
- [ ] Write unit tests with mocked filesystem

### Day 3-4: CLI Executor
```python
# src/agents/claude_code/cli_executor.py
class ClaudeCLIExecutor:
    """Executes Claude CLI commands with session management"""
    
    async def execute(
        workflow: str,
        message: str,
        workspace: Path,
        session_id: Optional[str] = None,
        max_turns: int = 2
    ) -> CLIResult:
        """Execute Claude CLI with streaming output"""
```

**Tasks**:
- [ ] Implement command builder with proper escaping
- [ ] Add subprocess management with asyncio
- [ ] Create stream parser for JSON output
- [ ] Implement session ID extraction
- [ ] Add timeout and resource limits
- [ ] Create comprehensive test suite

### Day 5: Database Schema
```sql
-- migrations/20250604_claude_cli_runs.sql
CREATE TABLE claude_cli_runs (
    run_id UUID PRIMARY KEY,
    session_id VARCHAR(255),
    workflow_name VARCHAR(50) NOT NULL,
    branch VARCHAR(255) NOT NULL,
    status VARCHAR(20) NOT NULL,
    workspace_path TEXT,
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    error_message TEXT,
    metadata JSONB
);

CREATE TABLE claude_cli_outputs (
    id SERIAL PRIMARY KEY,
    run_id UUID REFERENCES claude_cli_runs(run_id),
    timestamp TIMESTAMP NOT NULL,
    output_type VARCHAR(50),
    content JSONB,
    sequence_number INTEGER
);
```

**Tasks**:
- [ ] Create migration files
- [ ] Implement repository classes
- [ ] Add session tracking
- [ ] Create output storage
- [ ] Add indexes for performance

## Week 2: API & Streaming

### Day 1-2: REST API Implementation
```python
# src/api/routes/claude_cli_routes.py
@router.post("/agent/claude-code/{workflow_name}/run")
async def run_workflow(
    workflow_name: WorkflowType,
    request: RunWorkflowRequest,
    db: Database = Depends(get_db)
) -> RunWorkflowResponse:
    """Start Claude Code workflow execution"""
```

**Tasks**:
- [ ] Implement API endpoints
- [ ] Add request validation
- [ ] Create async task queueing
- [ ] Implement status endpoint
- [ ] Add error handling
- [ ] Write API tests

### Day 3-4: WebSocket Streaming
```python
# src/api/websocket/claude_stream.py
@router.websocket("/agent/claude-code/run/{run_id}/stream")
async def stream_output(
    websocket: WebSocket,
    run_id: str,
    db: Database = Depends(get_db)
):
    """Stream Claude CLI output via WebSocket"""
```

**Tasks**:
- [ ] Implement WebSocket endpoint
- [ ] Create stream multiplexing
- [ ] Add connection management
- [ ] Implement backpressure handling
- [ ] Add reconnection support
- [ ] Create integration tests

### Day 5: Session Management
```python
# src/agents/claude_code/session_manager.py
class ClaudeSessionManager:
    """Manages Claude CLI sessions across workflows"""
    
    async def create_session(run_id: str) -> str:
        """Create new session"""
        
    async def resume_session(session_id: str) -> SessionContext:
        """Resume existing session"""
        
    async def get_session_history(session_id: str) -> List[Message]:
        """Get session conversation history"""
```

**Tasks**:
- [ ] Implement session storage
- [ ] Add session resumption logic
- [ ] Create session expiration
- [ ] Add session analytics
- [ ] Implement cleanup policies

## Week 3: Genie Integration

### Day 1-2: Genie Tool Implementation
```python
# src/agents/genie/tools/claude_code_tool.py
class ClaudeCodeTool(BaseTool):
    """Tool for executing Claude Code workflows"""
    
    name = "claude_code_workflow"
    description = "Execute Claude Code workflows with streaming"
    
    async def run(
        self,
        workflow: str,
        message: str,
        branch: str,
        max_turns: int = 2,
        session_id: Optional[str] = None
    ) -> ToolResult:
        """Execute workflow and return result"""
```

**Tasks**:
- [ ] Create tool class
- [ ] Implement execution logic
- [ ] Add streaming support
- [ ] Create result parsing
- [ ] Add error handling
- [ ] Write tool tests

### Day 3-4: Orchestration Patterns
```python
# src/agents/genie/orchestration/epic_workflow.py
class EpicWorkflowOrchestrator:
    """Orchestrates epic execution using Claude Code"""
    
    async def execute_epic(self, epic_id: str):
        """Execute full epic workflow"""
        # 1. Architect
        # 2. Get approvals
        # 3. Implement
        # 4. Test
        # 5. Review
```

**Tasks**:
- [ ] Implement epic workflow
- [ ] Add approval handling
- [ ] Create state management
- [ ] Add rollback support
- [ ] Implement monitoring
- [ ] Create e2e tests

### Day 5: Memory Integration
**Tasks**:
- [ ] Store workflow decisions in memory
- [ ] Add session linking to memory
- [ ] Create learning patterns
- [ ] Implement failure tracking
- [ ] Add pattern recognition

## Week 4: Production Readiness

### Day 1-2: Security Hardening
**Tasks**:
- [ ] Implement input sanitization
- [ ] Add branch name validation
- [ ] Create execution sandboxing
- [ ] Add rate limiting
- [ ] Implement access controls
- [ ] Security audit

### Day 3: Performance Optimization
**Tasks**:
- [ ] Add repository caching
- [ ] Implement connection pooling
- [ ] Optimize stream processing
- [ ] Add response caching
- [ ] Profile and optimize
- [ ] Load testing

### Day 4: Monitoring & Observability
**Tasks**:
- [ ] Add Prometheus metrics
- [ ] Implement structured logging
- [ ] Create Grafana dashboards
- [ ] Add trace correlation
- [ ] Implement alerting
- [ ] Create runbooks

### Day 5: Documentation & Training
**Tasks**:
- [ ] Write user documentation
- [ ] Create API documentation
- [ ] Add workflow examples
- [ ] Create troubleshooting guide
- [ ] Record demo videos
- [ ] Team training session

## Milestones

### M1: Basic Execution (End of Week 1)
- CLI executor working
- Environment management complete
- Database schema deployed

### M2: Streaming API (End of Week 2)
- REST API functional
- WebSocket streaming working
- Session management operational

### M3: Genie Integration (End of Week 3)
- Claude Code tool implemented
- Epic orchestration working
- Memory integration complete

### M4: Production Ready (End of Week 4)
- Security hardened
- Performance optimized
- Fully documented

## Risk Mitigation

### Technical Risks
1. **CLI Stability**: Implement retry logic and fallbacks
2. **Session Corruption**: Add validation and recovery
3. **Resource Exhaustion**: Implement strict limits

### Operational Risks
1. **Workspace Cleanup**: Automated cleanup jobs
2. **Performance Degradation**: Capacity planning
3. **Security Vulnerabilities**: Regular audits

## Success Metrics

1. **Execution Reliability**: >99.5% success rate
2. **Performance**: <5s workspace setup time
3. **Streaming Latency**: <100ms end-to-end
4. **Session Recovery**: 100% resumption success
5. **Resource Usage**: <1GB per execution
6. **Concurrent Executions**: Support 50+ parallel

## Rollback Plan

If issues arise:
1. Feature flag to disable CLI mode
2. Fallback to container execution
3. Session migration tools
4. Data preservation strategy

## Dependencies

- Claude CLI v2.0+
- Python 3.11+
- PostgreSQL 15+
- Redis (for queueing)
- Git 2.40+

## Team Assignments

- **Infrastructure**: Environment, CLI executor
- **API Team**: REST, WebSocket, session management  
- **Integration**: Genie tool, orchestration
- **DevOps**: Security, monitoring, deployment