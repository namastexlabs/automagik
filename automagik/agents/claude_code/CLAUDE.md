# CLAUDE.md

This file provides Claude Code workflow system development context for Claude Code working in this directory.

## Claude Code Workflow System Development Context

This directory contains the Claude Code workflow orchestration system - the engine that powers Genie's ability to coordinate specialized workflows. When working here, you're developing the infrastructure that enables autonomous workflow execution and monitoring.

## 🤖 Workflow System Architecture

### Core Components
- **Agent** (`agent.py`) - Main workflow agent handling execution requests
- **Executors** (`executor_*.py`) - Different execution strategies (SDK, raw streams)
- **Stream Processing** (`stream_*.py`) - Real-time output processing and parsing
- **Progress Tracking** (`progress_tracker.py`, `completion_tracker.py`) - Workflow monitoring
- **Error Handling** (`error_handling.py`) - Comprehensive error recovery
- **Repository Utils** (`repository_utils.py`) - Git and workspace management

### Workflow Types
Each workflow in `workflows/` represents a specialized Claude Code agent:
- **genie** - Orchestrator consciousness that coordinates all other workflows
- **builder** - Implementation and feature development
- **guardian** - Testing, validation, and quality assurance
- **surgeon** - Bug fixing and issue resolution
- **shipper** - Deployment and release preparation
- **lina** - Linear integration and project management
- **brain** - Knowledge management and pattern storage

## 🚀 Workflow Execution Patterns

### SDK Execution Pattern
```python
# Primary execution method using Claude SDK
class SDKExecutor(ExecutorBase):
    async def execute_workflow(
        self,
        workflow_name: str,
        message: str,
        session_name: str,
        **kwargs
    ) -> WorkflowResult:
        """Execute workflow using Claude SDK."""
        
        # 1. Load workflow configuration
        config = await self.load_workflow_config(workflow_name)
        
        # 2. Initialize Claude client
        client = self.get_claude_client()
        
        # 3. Create execution context
        context = self.create_execution_context(
            workflow_name=workflow_name,
            session_name=session_name,
            workspace_path=self.workspace_path
        )
        
        # 4. Execute workflow with streaming
        stream = await client.messages.create(
            model="claude-3-5-sonnet-20241022",
            messages=[{"role": "user", "content": message}],
            system=config.prompt,
            tools=config.allowed_tools,
            stream=True,
            max_tokens=8192
        )
        
        # 5. Process stream with real-time parsing
        result = await self.process_workflow_stream(stream, context)
        
        return result
```

### Stream Processing Pattern
```python
# Real-time stream processing for workflow output
class SDKStreamProcessor:
    async def process_stream(
        self,
        stream: AsyncIterator,
        context: ExecutionContext
    ) -> WorkflowResult:
        """Process workflow execution stream."""
        
        accumulated_text = ""
        tool_calls = []
        
        async for event in stream:
            if event.type == "content_block_delta":
                # Accumulate text output
                if event.delta.type == "text":
                    text_chunk = event.delta.text
                    accumulated_text += text_chunk
                    
                    # Real-time progress parsing
                    await self.parse_progress_updates(text_chunk, context)
                    
            elif event.type == "tool_use":
                # Handle tool executions
                tool_call = await self.execute_tool_call(event.tool_use, context)
                tool_calls.append(tool_call)
                
        return WorkflowResult(
            output=accumulated_text,
            tool_calls=tool_calls,
            status="completed",
            context=context
        )
```

### Progress Tracking Pattern
```python
# Real-time workflow progress monitoring
class ProgressTracker:
    def __init__(self, workflow_name: str, session_name: str):
        self.workflow_name = workflow_name
        self.session_name = session_name
        self.progress_data = {
            "current_phase": "initializing",
            "steps_completed": 0,
            "total_steps": None,
            "last_update": None
        }
    
    async def update_progress(self, text_chunk: str):
        """Parse progress updates from workflow output."""
        
        # Parse completion indicators
        if "✅" in text_chunk:
            self.progress_data["steps_completed"] += 1
            
        # Parse phase transitions
        phase_patterns = {
            "Phase 1": "context_loading",
            "Phase 2": "implementation", 
            "Phase 3": "testing",
            "Phase 4": "documentation"
        }
        
        for pattern, phase in phase_patterns.items():
            if pattern in text_chunk:
                self.progress_data["current_phase"] = phase
                break
        
        # Track progress steps (percentage calculation removed per user request)
        
        # Store progress update
        await self.store_progress_update()
```

## 🔧 Workflow Configuration Patterns

### Workflow Structure
```python
# Each workflow has:
# - prompt.md: System prompt defining behavior
# - allowed_tools.json: Tools available to workflow
# - Configuration loaded dynamically

@dataclass
class WorkflowConfig:
    name: str
    prompt: str
    allowed_tools: List[str]
    max_tokens: int = 8192
    timeout: int = 300
    
    @classmethod
    async def load(cls, workflow_name: str) -> "WorkflowConfig":
        """Load workflow configuration from files."""
        
        base_path = Path(f"src/agents/claude_code/workflows/{workflow_name}")
        
        # Load prompt
        prompt_path = base_path / "prompt.md"
        with open(prompt_path) as f:
            prompt = f.read()
        
        # Load allowed tools
        tools_path = base_path / "allowed_tools.json"
        with open(tools_path) as f:
            allowed_tools = json.load(f)
        
        return cls(
            name=workflow_name,
            prompt=prompt,
            allowed_tools=allowed_tools
        )
```

### Tool Allowlisting Pattern
```json
// workflows/{workflow_name}/allowed_tools.json
[
  {
    "type": "computer_20241022",
    "name": "computer"
  },
  {
    "type": "text_editor_20241022", 
    "name": "str_replace_editor"
  },
  {
    "type": "bash",
    "name": "bash"
  }
]
```

## 📊 Workflow Monitoring Patterns

### Execution Context Tracking
```python
# Comprehensive execution context for monitoring
@dataclass
class ExecutionContext:
    run_id: str
    workflow_name: str
    session_name: str
    workspace_path: str
    start_time: datetime
    status: str = "running"
    progress: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)
    
    def update_status(self, status: str, details: Optional[str] = None):
        """Update execution status."""
        self.status = status
        if details:
            self.progress["status_details"] = details
        
        # Store status update in database
        asyncio.create_task(self.persist_status_update())
```

### Error Recovery Pattern
```python
# Comprehensive error handling with recovery
class WorkflowErrorHandler:
    async def handle_execution_error(
        self,
        error: Exception,
        context: ExecutionContext
    ) -> WorkflowRecoveryAction:
        """Handle workflow execution errors."""
        
        error_type = type(error).__name__
        
        # Timeout errors - extend execution time
        if isinstance(error, asyncio.TimeoutError):
            return WorkflowRecoveryAction.EXTEND_TIMEOUT
            
        # Rate limit errors - implement backoff
        elif "rate_limit" in str(error).lower():
            return WorkflowRecoveryAction.RATE_LIMIT_BACKOFF
            
        # Authentication errors - fail immediately
        elif "authentication" in str(error).lower():
            return WorkflowRecoveryAction.FAIL_IMMEDIATELY
            
        # Tool execution errors - retry with fallback
        elif "tool_use" in str(error).lower():
            return WorkflowRecoveryAction.RETRY_WITH_FALLBACK
            
        # Generic errors - retry once
        else:
            if context.retry_count < 1:
                return WorkflowRecoveryAction.RETRY_ONCE
            else:
                return WorkflowRecoveryAction.FAIL_WITH_REPORT
```

## 🔄 Workflow Orchestration Patterns

### Genie Orchestration Interface
```python
# Interface for Genie to spawn and monitor workflows
class WorkflowOrchestrator:
    async def spawn_workflow(
        self,
        workflow_name: str,
        message: str,
        session_name: str,
        **kwargs
    ) -> str:
        """Spawn a new workflow execution."""
        
        run_id = str(uuid.uuid4())
        
        # Create execution context
        context = ExecutionContext(
            run_id=run_id,
            workflow_name=workflow_name,
            session_name=session_name,
            workspace_path=self.workspace_path
        )
        
        # Start execution asynchronously
        task = asyncio.create_task(
            self.execute_workflow_async(context, message, **kwargs)
        )
        
        # Register task for monitoring
        self.active_workflows[run_id] = task
        
        return run_id
    
    async def get_workflow_status(self, run_id: str) -> WorkflowStatus:
        """Get current workflow status."""
        
        if run_id not in self.active_workflows:
            return WorkflowStatus.NOT_FOUND
            
        task = self.active_workflows[run_id]
        
        if task.done():
            if task.exception():
                return WorkflowStatus.FAILED
            else:
                return WorkflowStatus.COMPLETED
        else:
            return WorkflowStatus.RUNNING
```

### Autonomous Monitoring Integration
```python
# Integration with Genie's autonomous monitoring
class WorkflowMonitor:
    async def monitor_workflow_progress(
        self,
        run_id: str,
        check_interval: int = 30
    ) -> AsyncIterator[ProgressUpdate]:
        """Monitor workflow progress for autonomous systems."""
        
        while True:
            status = await self.get_detailed_status(run_id)
            
            yield ProgressUpdate(
                run_id=run_id,
                current_phase=status.progress.current_phase,
                estimated_remaining=status.progress.estimated_remaining,
                status=status.status
            )
            
            # Exit conditions
            if status.status in ["completed", "failed", "cancelled"]:
                break
                
            await asyncio.sleep(check_interval)
```

## 🛠️ Development Commands for Workflow System

```bash
# Test workflow execution locally
uv run python -m src.agents.claude_code.debug_builder \
  --workflow builder \
  --message "Implement authentication system"

# Monitor workflow execution
uv run python -c "
from src.agents.claude_code.progress_tracker import get_workflow_status
print(get_workflow_status('run-id-123'))
"

# Test stream processing
uv run python -m src.agents.claude_code.sdk_stream_processor \
  --test-mode

# Debug workflow configuration loading
uv run python -c "
from src.agents.claude_code.models import WorkflowConfig
config = WorkflowConfig.load('builder')
print(config.allowed_tools)
"

# Test error handling
uv run python -m src.agents.claude_code.error_handling \
  --simulate-error timeout
```

## 🧪 Workflow System Testing Patterns

### Workflow Execution Testing
```python
@pytest.mark.asyncio
async def test_workflow_execution():
    """Test complete workflow execution."""
    
    orchestrator = WorkflowOrchestrator()
    
    # Start workflow
    run_id = await orchestrator.spawn_workflow(
        workflow_name="builder",
        message="Create a simple hello world function",
        session_name="test_session"
    )
    
    # Monitor progress
    status = await orchestrator.get_workflow_status(run_id)
    assert status == WorkflowStatus.RUNNING
    
    # Wait for completion
    await orchestrator.wait_for_completion(run_id, timeout=60)
    
    final_status = await orchestrator.get_workflow_status(run_id)
    assert final_status == WorkflowStatus.COMPLETED
```

### Stream Processing Testing
```python
def test_stream_parsing():
    """Test workflow output stream parsing."""
    
    processor = SDKStreamProcessor()
    
    # Mock stream events
    mock_events = [
        {"type": "content_block_delta", "delta": {"text": "Starting Phase 1..."}},
        {"type": "content_block_delta", "delta": {"text": "✅ Task completed"}},
        {"type": "tool_use", "tool_use": {"name": "str_replace_editor", "input": {}}}
    ]
    
    # Process events
    result = await processor.process_mock_stream(mock_events)
    
    assert "Phase 1" in result.output
    assert result.progress["steps_completed"] == 1
    assert len(result.tool_calls) == 1
```

## 🔍 Workflow System Debugging

```bash
# Enable comprehensive debugging
export CLAUDE_CODE_DEBUG=true
export AUTOMAGIK_LOG_LEVEL=DEBUG

# Test specific workflow prompt
uv run python -c "
from src.agents.claude_code.models import WorkflowConfig
config = WorkflowConfig.load('genie')
print(config.prompt[:500])
"

# Monitor active workflow executions
uv run python -c "
from src.agents.claude_code.agent import get_active_workflows
for run_id, status in get_active_workflows().items():
    print(f'{run_id}: {status}')
"

# Debug stream processing
export STREAUTOMAGIK_DEBUG=true
# Then run any workflow to see detailed stream processing logs
```

## ⚠️ Workflow System Development Guidelines

### Execution Safety
- Always use timeout mechanisms for workflow execution
- Implement proper error recovery and fallback strategies
- Use resource limits to prevent runaway executions
- Monitor workspace changes and implement rollback capabilities

### Performance Optimization
- Use streaming for real-time progress updates
- Implement efficient progress parsing without blocking execution
- Cache workflow configurations for repeated executions
- Use async patterns throughout for non-blocking operations

### Monitoring Integration
- Provide detailed progress information for autonomous monitoring
- Implement standardized status reporting across all workflows
- Support real-time status queries for external systems
- Store execution metrics for performance analysis

### Security Considerations
- Validate all workflow inputs and configurations
- Restrict file system access to designated workspace areas
- Implement tool execution sandboxing
- Log all workflow actions for audit trails

This context focuses specifically on Claude Code workflow system development and should be used alongside the global development rules in the root CLAUDE.md.