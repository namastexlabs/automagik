# Claude CLI Workflow Orchestration Architecture

## Executive Summary

This architecture defines a system where Genie orchestrates Claude Code workflows using Claude CLI with session management. Each workflow executes in an isolated environment with streaming JSON output for real-time monitoring and control.

## System Overview

```mermaid
graph TB
    subgraph "Genie Orchestrator"
        G[Genie Agent]
        T[Claude Code Tool]
        SM[Session Manager]
    end
    
    subgraph "Claude Code API Layer"
        API[REST API]
        RM[Run Manager]
        SQ[Status Queue]
    end
    
    subgraph "Execution Layer"
        CE[CLI Executor]
        EM[Environment Manager]
        SP[Session Persistence]
    end
    
    subgraph "Isolated Workspace"
        TMP[/tmp/claude-code-{run_id}]
        REPO[Cloned Repository]
        CONFIG[.env, .mcp.json, allowed_tools.json]
        CLI[Claude CLI Process]
    end
    
    G --> T
    T --> API
    API --> RM
    RM --> CE
    CE --> EM
    EM --> TMP
    TMP --> REPO
    TMP --> CONFIG
    TMP --> CLI
    CLI --> SP
    RM --> SQ
    G -.->|Stream JSON| CLI
```

## Core Components

### 1. Genie Integration

#### Claude Code Tool Definition
```python
@dataclass
class ClaudeCodeTool:
    """Tool for Genie to execute Claude Code workflows"""
    
    name: str = "claude_code_workflow"
    description: str = "Execute Claude Code workflows with streaming output"
    
    class Config:
        workflow_name: str  # architect, implement, test, etc.
        branch: str  # Git branch to checkout
        message: str  # User message/prompt
        max_turns: int = 2  # Claude CLI max turns
        session_id: Optional[str] = None  # Resume existing session
        stream_output: bool = True  # Enable JSON streaming
```

### 2. API Design

#### Endpoints
```yaml
/api/v1/agent/claude-code/{workflow_name}/run:
  post:
    summary: Execute Claude Code workflow
    parameters:
      - name: workflow_name
        in: path
        required: true
        schema:
          type: string
          enum: [architect, implement, test, review, document, fix, refactor, pr]
    requestBody:
      content:
        application/json:
          schema:
            type: object
            required: [branch, message]
            properties:
              branch:
                type: string
                description: Git branch to checkout
              message:
                type: string
                description: User message/prompt
              max_turns:
                type: integer
                default: 2
              session_id:
                type: string
                description: Resume existing session
              stream:
                type: boolean
                default: true
    responses:
      200:
        description: Workflow execution started
        content:
          application/json:
            schema:
              type: object
              properties:
                run_id:
                  type: string
                session_id:
                  type: string
                status:
                  type: string
                  enum: [queued, running, completed, failed]
                stream_url:
                  type: string
                  description: WebSocket URL for streaming output

/api/v1/agent/claude-code/run/{run_id}/status:
  get:
    summary: Get workflow run status
    responses:
      200:
        description: Run status
        content:
          application/json:
            schema:
              type: object
              properties:
                run_id:
                  type: string
                session_id:
                  type: string
                status:
                  type: string
                  enum: [queued, running, completed, failed]
                progress:
                  type: object
                  properties:
                    turns_completed:
                      type: integer
                    max_turns:
                      type: integer
                    last_output:
                      type: string
                result:
                  type: object
                  description: Final result (when completed)
                error:
                  type: string
                  description: Error message (when failed)

/api/v1/agent/claude-code/run/{run_id}/stream:
  get:
    summary: WebSocket endpoint for streaming output
    description: Connects to live JSON stream from Claude CLI
```

### 3. Execution Environment

#### Environment Manager
```python
@dataclass
class ExecutionEnvironment:
    """Manages isolated execution environments"""
    
    run_id: str
    workspace_path: Path  # /tmp/claude-code-{run_id}
    repo_path: Path
    branch: str
    
    async def setup(self):
        """Set up isolated environment"""
        # 1. Create workspace directory
        self.workspace_path.mkdir(parents=True, exist_ok=True)
        
        # 2. Clone repository
        await self._clone_repository()
        
        # 3. Checkout branch
        await self._checkout_branch()
        
        # 4. Copy configuration files
        await self._copy_configs()
        
    async def _clone_repository(self):
        """Clone repo to isolated workspace"""
        cmd = f"git clone /root/workspace/am-agents-labs {self.repo_path}"
        await run_command(cmd)
        
    async def _checkout_branch(self):
        """Checkout specified branch"""
        cmd = f"cd {self.repo_path} && git checkout {self.branch}"
        await run_command(cmd)
        
    async def _copy_configs(self):
        """Copy required config files"""
        configs = [".env", ".mcp.json", "allowed_tools.json"]
        for config in configs:
            src = Path("/root/workspace/am-agents-labs") / config
            dst = self.workspace_path / config
            if src.exists():
                shutil.copy2(src, dst)
    
    async def cleanup(self):
        """Clean up workspace after execution"""
        if self.workspace_path.exists():
            shutil.rmtree(self.workspace_path)
```

### 4. CLI Executor

#### Session Management
```python
@dataclass
class ClaudeSession:
    """Manages Claude CLI sessions"""
    
    session_id: Optional[str] = None
    run_id: str
    workflow_name: str
    max_turns: int = 2
    
    def build_command(self, message: str, workspace: Path) -> List[str]:
        """Build Claude CLI command"""
        cmd = ["claude"]
        
        # Resume session if provided
        if self.session_id:
            cmd.extend(["-r", self.session_id])
        
        cmd.extend([
            "-p",
            "--output-format", "stream-json",
            "--max-turns", str(self.max_turns),
            "--mcp-config", ".mcp.json",
            "--allowedTools", "$(cat allowed_tools.json)",
            "--system-prompt", f"$(cat src/agents/claude_code/workflows/{self.workflow_name}/prompt.md)",
            message,
            "--verbose"
        ])
        
        return cmd
```

#### Stream Processing
```python
class StreamProcessor:
    """Processes Claude CLI JSON stream"""
    
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.session_id: Optional[str] = None
        self.messages: List[Dict] = []
        
    async def process_line(self, line: str):
        """Process a line from Claude CLI output"""
        try:
            data = json.loads(line)
            
            # Extract session ID from init message
            if data.get("type") == "system" and data.get("subtype") == "init":
                self.session_id = data.get("session_id")
            
            # Store message for analysis
            self.messages.append(data)
            
            # Forward to WebSocket
            await self.websocket.send_json(data)
            
            # Detect completion
            if data.get("type") == "result":
                return data
                
        except json.JSONDecodeError:
            # Handle non-JSON output
            await self.websocket.send_text(line)
```

### 5. Integration Patterns

#### Genie Tool Usage
```python
class GenieOrchestrator:
    """Example of Genie using Claude Code as a tool"""
    
    async def handle_epic(self, epic_id: str):
        # 1. Architect phase
        architect_result = await self.call_claude_code(
            workflow="architect",
            branch=f"NMSTX-{epic_id}",
            message=f"Design architecture for epic {epic_id}",
            max_turns=5
        )
        
        # 2. Parse streaming output
        decisions = self.extract_decisions(architect_result)
        
        # 3. Human approval if needed
        if decisions.needs_approval:
            await self.request_human_approval(decisions)
        
        # 4. Continue to implementation
        impl_result = await self.call_claude_code(
            workflow="implement",
            branch=f"NMSTX-{epic_id}",
            message="Implement the approved architecture",
            session_id=architect_result.session_id,  # Resume context
            max_turns=10
        )
```

## Key Design Decisions

### 1. Isolated Execution Environments
- **Decision**: Each workflow runs in `/tmp/claude-code-{run_id}`
- **Rationale**: Complete isolation, clean state, parallel execution
- **Alternatives Rejected**: 
  - Shared workspace: Risk of conflicts
  - Docker volumes: Added complexity

### 2. Session Persistence
- **Decision**: Use Claude CLI's `-r` flag for session resumption
- **Rationale**: Maintain context across workflow phases
- **Implementation**: Store session_id in database, pass between calls

### 3. Streaming Architecture
- **Decision**: JSON streaming via WebSocket for real-time monitoring
- **Rationale**: Genie can observe progress and intervene if needed
- **Alternatives Rejected**:
  - Polling: Too much delay
  - Batch output: No real-time visibility

### 4. Configuration Management
- **Decision**: Copy `.env`, `.mcp.json`, `allowed_tools.json` to workspace
- **Rationale**: Claude CLI requires these files in working directory
- **Security**: Never include secrets in git

## Security Considerations

1. **Workspace Isolation**: Each run in separate `/tmp` directory
2. **Branch Restrictions**: Validate branch names, prevent injection
3. **Tool Restrictions**: Workflow-specific `allowed_tools.json`
4. **Resource Limits**: Implement timeouts and memory limits
5. **Cleanup**: Automatic workspace deletion after completion

## Performance Optimization

1. **Repository Caching**: Keep bare repo locally, clone from it
2. **Parallel Execution**: Multiple workspaces can run concurrently
3. **Session Reuse**: Resume sessions to avoid re-analysis
4. **Streaming**: No buffering, immediate output

## Error Handling

1. **CLI Failures**: Capture exit codes, stderr
2. **Timeout Handling**: Kill processes exceeding limits
3. **Cleanup Guarantee**: Always remove workspace, even on error
4. **Session Recovery**: Allow resuming failed sessions

## Monitoring & Observability

1. **Metrics**:
   - Workflow execution time
   - Session creation/resumption rate
   - Error rates by workflow type
   - Resource usage per run

2. **Logging**:
   - Full Claude CLI output to files
   - Structured logs for analysis
   - Session tracking

3. **Tracing**:
   - Correlation IDs across Genie/Claude Code
   - Decision tracking through memory

## Implementation Roadmap

### Phase 1: Core Infrastructure (Week 1)
- [ ] Environment Manager implementation
- [ ] CLI Executor with session support
- [ ] Basic API endpoints
- [ ] Workspace lifecycle management

### Phase 2: Streaming & Integration (Week 2)
- [ ] WebSocket streaming implementation
- [ ] Genie tool integration
- [ ] Session persistence
- [ ] Error handling & recovery

### Phase 3: Production Readiness (Week 3)
- [ ] Security hardening
- [ ] Performance optimization
- [ ] Monitoring & metrics
- [ ] Documentation & examples

### Phase 4: Advanced Features (Week 4)
- [ ] Multi-branch workflows
- [ ] Parallel execution optimization
- [ ] Advanced session management
- [ ] Cost tracking integration

## Success Criteria

1. **Functional**:
   - All 8 workflows executable via API
   - Session resumption working
   - Real-time streaming operational
   - Genie integration complete

2. **Performance**:
   - Workspace setup < 5 seconds
   - Streaming latency < 100ms
   - Concurrent execution support

3. **Reliability**:
   - 99% cleanup success rate
   - Graceful error handling
   - Session recovery capability

4. **Security**:
   - No credential leakage
   - Complete workspace isolation
   - Resource limit enforcement

## Migration Strategy

1. **Parallel Operation**: Keep container-based execution as fallback
2. **Feature Flag**: `CLAUDE_CODE_EXECUTION_MODE=cli|container`
3. **Gradual Rollout**: Start with non-critical workflows
4. **Rollback Plan**: Revert to container mode if issues arise